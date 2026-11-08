"""FastAPI REST endpoints for workflow templates."""

from typing import Optional, List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.workflow import WorkflowTemplate
from app.schemas.workflow import (
    WorkflowTemplateResponse,
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
)
from app.services.orchestration.templates import get_standard_templates, get_template_by_key

router = APIRouter(prefix="", tags=["Workflow Templates"])


async def _get_channel_for_user(
    db: AsyncSession, channel_id: Optional[UUID], user: User
) -> Optional[Channel]:
    if not channel_id:
        stmt = select(Channel).where(Channel.user_id == user.id)
        res = await db.execute(stmt)
        return res.scalars().first()

    stmt = select(Channel).where(Channel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if user.role != "SUPER_ADMIN" and channel.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized channel access")
    return channel


@router.get("", response_model=List[WorkflowTemplateResponse])
async def list_templates(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all available system templates plus channel-specific custom templates."""
    channel = await _get_channel_for_user(db, channel_id, current_user)

    # 1. Start with standard built-in templates
    std_templates = get_standard_templates()
    response_list: List[WorkflowTemplateResponse] = []
    for st in std_templates:
        response_list.append(
            WorkflowTemplateResponse(
                id=None,
                template_key=st["template_key"],
                name=st["name"],
                description=st["description"],
                content_format=st["content_format"],
                estimated_duration_sec=st["estimated_duration_sec"],
                stages=st["stages"],
                default_settings=st["default_settings"],
                is_system=True,
                channel_id=None,
            )
        )

    # 2. Add custom templates from DB
    if channel:
        stmt = select(WorkflowTemplate).where(WorkflowTemplate.channel_id == channel.id)
        db_templates = (await db.execute(stmt)).scalars().all()
        for dt in db_templates:
            response_list.append(WorkflowTemplateResponse.model_validate(dt))

    return response_list


@router.post("", response_model=WorkflowTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: WorkflowTemplateCreate,
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a channel-scoped custom workflow template."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    if not channel:
        raise HTTPException(status_code=400, detail="Channel context required to create custom templates")

    template_key = f"CUSTOM_{channel.id}_{uuid4().hex[:8]}"
    template = WorkflowTemplate(
        template_key=template_key,
        name=payload.name,
        description=payload.description,
        content_format=payload.content_format,
        estimated_duration_sec=payload.estimated_duration_sec,
        stages=payload.stages,
        default_settings=payload.default_settings or {},
        is_system=False,
        channel_id=channel.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return WorkflowTemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get template by UUID or system template_key."""
    # Check system templates first
    sys_tpl = get_template_by_key(template_id)
    if sys_tpl:
        return WorkflowTemplateResponse(
            id=None,
            template_key=sys_tpl["template_key"],
            name=sys_tpl["name"],
            description=sys_tpl["description"],
            content_format=sys_tpl["content_format"],
            estimated_duration_sec=sys_tpl["estimated_duration_sec"],
            stages=sys_tpl["stages"],
            default_settings=sys_tpl["default_settings"],
            is_system=True,
            channel_id=None,
        )

    # Check database
    try:
        tpl_uuid = UUID(template_id)
        stmt = select(WorkflowTemplate).where(WorkflowTemplate.id == tpl_uuid)
        res = await db.execute(stmt)
        template = res.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        if not template.is_system:
            await _get_channel_for_user(db, template.channel_id, current_user)
        return WorkflowTemplateResponse.model_validate(template)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@router.patch("/{template_id}", response_model=WorkflowTemplateResponse)
async def update_template(
    template_id: UUID,
    payload: WorkflowTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom workflow template."""
    stmt = select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    template = (await db.execute(stmt)).scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=403, detail="System templates cannot be modified")

    await _get_channel_for_user(db, template.channel_id, current_user)

    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    if payload.content_format is not None:
        template.content_format = payload.content_format
    if payload.estimated_duration_sec is not None:
        template.estimated_duration_sec = payload.estimated_duration_sec
    if payload.stages is not None:
        template.stages = payload.stages
    if payload.default_settings is not None:
        template.default_settings = payload.default_settings

    await db.commit()
    await db.refresh(template)
    return WorkflowTemplateResponse.model_validate(template)


@router.post("/{template_id}/duplicate", response_model=WorkflowTemplateResponse)
async def duplicate_template(
    template_id: str,
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate an existing template into a channel-scoped custom template."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    if not channel:
        raise HTTPException(status_code=400, detail="Channel context required")

    source_data = None
    sys_tpl = get_template_by_key(template_id)
    if sys_tpl:
        source_data = sys_tpl
    else:
        try:
            tpl_uuid = UUID(template_id)
            stmt = select(WorkflowTemplate).where(WorkflowTemplate.id == tpl_uuid)
            db_tpl = (await db.execute(stmt)).scalars().first()
            if db_tpl:
                if not db_tpl.is_system:
                    await _get_channel_for_user(db, db_tpl.channel_id, current_user)
                source_data = {
                    "name": db_tpl.name,
                    "description": db_tpl.description,
                    "content_format": db_tpl.content_format,
                    "estimated_duration_sec": db_tpl.estimated_duration_sec,
                    "stages": db_tpl.stages,
                    "default_settings": db_tpl.default_settings,
                }
        except ValueError:
            pass

    if not source_data:
        raise HTTPException(status_code=404, detail="Source template not found")

    new_key = f"COPY_{source_data.get('template_key', 'TPL')}_{uuid4().hex[:6]}"
    new_template = WorkflowTemplate(
        template_key=new_key,
        name=f"Copy of {source_data['name']}",
        description=source_data["description"],
        content_format=source_data["content_format"],
        estimated_duration_sec=source_data["estimated_duration_sec"],
        stages=source_data["stages"],
        default_settings=source_data["default_settings"],
        is_system=False,
        channel_id=channel.id,
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    return WorkflowTemplateResponse.model_validate(new_template)

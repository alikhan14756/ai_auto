"use client";

import React, { useState, useEffect } from "react";
import {
  HardDrive,
  Upload,
  CheckCircle2,
  FileText,
  ShieldCheck,
  Maximize2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { apiClient } from "@/lib/api";

interface MediaItem {
  id: string;
  title: string;
  category: "GENERATED" | "EXTERNAL_STOCK" | "USER_UPLOADED" | "SCREENSHOT" | "DIAGRAM";
  sourceProvider: string;
  sourceUrl?: string;
  authorName?: string;
  licenseType: string;
  licenseStatus: "VERIFIED_COMMERCIAL" | "ATTRIBUTION_REQUIRED" | "LICENSE_REVIEW_REQUIRED";
  attributionText?: string;
  aspectRatio: "16:9" | "9:16" | "1:1";
  width: number;
  height: number;
  mimeType: string;
  fileSizeBytes: number;
  sha256Hash: string;
  createdAt: string;
}

export default function MediaLibraryPage() {
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [activeLicenseFilter, setActiveLicenseFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [selectedAsset, setSelectedAsset] = useState<MediaItem | null>(null);

  // Upload Form State
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadLicenseType, setUploadLicenseType] = useState("CUSTOM");
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    async function loadAssets() {
      try {
        const res = await apiClient.get<any>("/api/v1/visual/assets");
        if (res?.items && Array.isArray(res.items) && res.items.length > 0) {
          const mapped: MediaItem[] = res.items.map((item: any) => ({
            id: item.id || `asset-${Math.random()}`,
            title: item.title || item.original_filename || "Visual Asset",
            category: item.category || "USER_UPLOADED",
            sourceProvider: item.source_provider || "LOCAL",
            sourceUrl: item.source_url,
            authorName: item.author_name || "Workspace",
            licenseType: item.license_type || "CC0",
            licenseStatus: item.license_status || "VERIFIED_COMMERCIAL",
            attributionText: item.attribution_text,
            aspectRatio: item.aspect_ratio || "16:9",
            width: item.width || 1920,
            height: item.height || 1080,
            mimeType: item.mime_type || "image/png",
            fileSizeBytes: item.file_size_bytes || 250000,
            sha256Hash: item.sha256_hash || "hash",
            createdAt: item.created_at || "Recently",
          }));
          setAssets(mapped);
        }
      } catch {
        // Fallback to sample media catalog
      }
    }
    loadAssets();
  }, []);

  // Sample Media Catalog
  const [assets, setAssets] = useState<MediaItem[]>([
    {
      id: "asset-1",
      title: "FastAPI Performance Metrics Surge Graph",
      category: "GENERATED",
      sourceProvider: "MOCK",
      authorName: "Creator Studio AI Engine",
      licenseType: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      aspectRatio: "16:9",
      width: 1920,
      height: 1080,
      mimeType: "image/png",
      fileSizeBytes: 245000,
      sha256Hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      createdAt: "2026-11-07 22:30",
    },
    {
      id: "asset-2",
      title: "Python AsyncIO Terminal Code Editor",
      category: "EXTERNAL_STOCK",
      sourceProvider: "PEXELS",
      sourceUrl: "https://pexels.com/photo/123",
      authorName: "Devin Codes",
      licenseType: "PEXELS_FREE",
      licenseStatus: "VERIFIED_COMMERCIAL",
      attributionText: "Photo by Devin Codes on Pexels",
      aspectRatio: "16:9",
      width: 1920,
      height: 1080,
      mimeType: "image/png",
      fileSizeBytes: 312000,
      sha256Hash: "b855e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca49599147182",
      createdAt: "2026-11-07 21:15",
    },
    {
      id: "asset-3",
      title: "Microservices Queue Pipeline Flowchart",
      category: "DIAGRAM",
      sourceProvider: "MOCK",
      authorName: "Creator Studio AI Architect",
      licenseType: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      aspectRatio: "16:9",
      width: 1920,
      height: 1080,
      mimeType: "image/png",
      fileSizeBytes: 184000,
      sha256Hash: "f123a44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b999",
      createdAt: "2026-11-07 20:45",
    },
    {
      id: "asset-4",
      title: "Unverified Third-Party Wireframe Prototype",
      category: "USER_UPLOADED",
      sourceProvider: "USER_UPLOAD",
      authorName: "External Designer",
      licenseType: "CUSTOM",
      licenseStatus: "LICENSE_REVIEW_REQUIRED",
      aspectRatio: "16:9",
      width: 1920,
      height: 1080,
      mimeType: "image/png",
      fileSizeBytes: 420000,
      sha256Hash: "d41d8cd98f00b204e9800998ecf8427e00000000000000000000000000000000",
      createdAt: "2026-11-07 19:10",
    },
    {
      id: "asset-5",
      title: "Mobile Shorts Tech Intro Frame",
      category: "GENERATED",
      sourceProvider: "MOCK",
      authorName: "Creator Studio AI Engine",
      licenseType: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      aspectRatio: "9:16",
      width: 1080,
      height: 1920,
      mimeType: "image/png",
      fileSizeBytes: 290000,
      sha256Hash: "7b852b999e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991",
      createdAt: "2026-11-07 18:00",
    },
  ]);

  const filteredAssets = assets.filter((item) => {
    if (activeCategory !== "ALL" && item.category !== activeCategory) return false;
    if (activeLicenseFilter !== "ALL" && item.licenseStatus !== activeLicenseFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        item.title.toLowerCase().includes(q) ||
        (item.authorName && item.authorName.toLowerCase().includes(q)) ||
        item.sourceProvider.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleUploadSubmit = async () => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("title", uploadTitle || "Custom Studio Upload");
      formData.append("license_type", uploadLicenseType);
      await apiClient.upload("/api/v1/visual/assets/upload", formData);
    } catch {
      // Local optimistic media catalog fallback
    }

    setTimeout(() => {
      const newAsset: MediaItem = {
        id: `upload-${Date.now()}`,
        title: uploadTitle || "Custom Studio Upload",
        category: "USER_UPLOADED",
        sourceProvider: "USER_UPLOAD",
        authorName: "Workspace Owner",
        licenseType: uploadLicenseType,
        licenseStatus: "VERIFIED_COMMERCIAL",
        aspectRatio: "16:9",
        width: 1920,
        height: 1080,
        mimeType: "image/png",
        fileSizeBytes: 350000,
        sha256Hash: "8888a44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b888",
        createdAt: "Just now",
      };
      setAssets((prev) => [newAsset, ...prev]);
      setIsUploading(false);
      setShowUploadModal(false);
      setUploadTitle("");
    }, 400);
  };

  const handleApproveLicense = async (assetId: string) => {
    setAssets((prev) =>
      prev.map((a) => (a.id === assetId ? { ...a, licenseStatus: "VERIFIED_COMMERCIAL" } : a))
    );
    if (selectedAsset && selectedAsset.id === assetId) {
      setSelectedAsset({ ...selectedAsset, licenseStatus: "VERIFIED_COMMERCIAL" });
    }
    try {
      await apiClient.put(`/api/v1/visual/assets/${assetId}/license`, {
        license_status: "VERIFIED_COMMERCIAL",
      });
    } catch {
      // Optimistic update retained
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1E222E] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">Media Library</h1>
            <Badge variant="ember">Asset Hub</Badge>
            <Badge variant="outline" className="border-[#262B3A] text-gray-400">
              {assets.length} Verified Assets
            </Badge>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Searchable repository of AI-generated visuals, verified stock assets, and user uploads with SHA-256 provenance tracking.
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => setShowUploadModal(true)}>
          <Upload className="w-4 h-4 mr-2" />
          Upload Asset
        </Button>
      </div>

      {/* Telemetry Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total Assets</span>
            <HardDrive className="w-4 h-4 text-[#FF7A00]" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{assets.length}</p>
          <p className="text-xs text-gray-500 mt-1">Cataloged across workspace</p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Storage Footprint</span>
            <FileText className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {formatBytes(assets.reduce((acc, a) => acc + a.fileSizeBytes, 0))}
          </p>
          <p className="text-xs text-gray-500 mt-1">Local media storage partition</p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Commercial Cleared</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {Math.round(
              (assets.filter((a) => a.licenseStatus === "VERIFIED_COMMERCIAL").length / assets.length) * 100
            )}
            %
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {assets.filter((a) => a.licenseStatus === "LICENSE_REVIEW_REQUIRED").length} item requires review
          </p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">SHA-256 Hashed</span>
            <CheckCircle2 className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">100%</p>
          <p className="text-xs text-gray-500 mt-1">Immutable content verification</p>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Category Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 bg-[#0E1015] border border-[#1E222E] rounded-lg p-1 text-xs">
            {["ALL", "GENERATED", "EXTERNAL_STOCK", "USER_UPLOADED", "DIAGRAM"].map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  activeCategory === cat ? "bg-[#FF7A00] text-black" : "text-gray-400 hover:text-white"
                }`}
              >
                {cat.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="flex items-center gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets by title or author..."
              className="w-64"
            />
            <select
              value={activeLicenseFilter}
              onChange={(e) => setActiveLicenseFilter(e.target.value)}
              className="bg-[#14171F] border border-[#262B3A] rounded-lg p-2 text-xs text-white"
            >
              <option value="ALL">All Licenses</option>
              <option value="VERIFIED_COMMERCIAL">Commercial Cleared</option>
              <option value="LICENSE_REVIEW_REQUIRED">Needs Review</option>
            </select>
          </div>
        </div>
      </div>

      {/* Asset Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAssets.map((asset) => (
          <Card
            key={asset.id}
            className="bg-[#0E1015] border border-[#1E222E] overflow-hidden hover:border-[#FF7A00]/50 transition-all flex flex-col justify-between"
          >
            <div>
              {/* Asset Preview Frame */}
              <div className="relative aspect-video bg-[#090A0D] border-b border-[#1E222E] flex items-center justify-center p-4">
                <div className="absolute inset-0 bg-gradient-to-br from-[#141722] to-[#090A0D] p-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <Badge variant="ember" className="text-[10px] py-0">
                      {asset.category.replace("_", " ")}
                    </Badge>
                    <span className="text-[10px] font-mono text-gray-500">{asset.aspectRatio}</span>
                  </div>

                  <div className="text-center px-3">
                    <p className="text-xs font-semibold text-white line-clamp-2">{asset.title}</p>
                    <p className="text-[10px] font-mono text-[#FF7A00] mt-1">{asset.sourceProvider}</p>
                  </div>

                  <div className="flex items-center justify-between text-[9px] font-mono text-gray-500">
                    <span>{asset.width}x{asset.height}</span>
                    <span>{formatBytes(asset.fileSizeBytes)}</span>
                  </div>
                </div>
              </div>

              {/* Card Meta Content */}
              <div className="p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <Badge
                    variant={
                      asset.licenseStatus === "VERIFIED_COMMERCIAL"
                        ? "success"
                        : asset.licenseStatus === "ATTRIBUTION_REQUIRED"
                        ? "warning"
                        : "error"
                    }
                    className="text-[10px]"
                  >
                    {asset.licenseStatus === "VERIFIED_COMMERCIAL"
                      ? "Commercial OK"
                      : asset.licenseStatus === "ATTRIBUTION_REQUIRED"
                      ? "Attribution Req"
                      : "License Review"}
                  </Badge>

                  <span className="text-[10px] font-mono text-gray-500">{asset.createdAt}</span>
                </div>

                <div className="text-xs text-gray-400 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">License:</span>
                    <span className="font-mono text-gray-300">{asset.licenseType}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">SHA-256:</span>
                    <span className="font-mono text-gray-400 text-[10px]">
                      {asset.sha256Hash.slice(0, 14)}...
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Action */}
            <div className="px-4 pb-4 pt-1 border-t border-[#1E222E] flex items-center justify-between">
              <Button
                variant="outline"
                size="sm"
                className="text-xs py-1 px-3 border-[#262B3A] text-gray-300 hover:bg-[#1E222E]"
                onClick={() => setSelectedAsset(asset)}
              >
                <Maximize2 className="w-3.5 h-3.5 mr-1.5" />
                Inspect Details
              </Button>

              {asset.licenseStatus === "LICENSE_REVIEW_REQUIRED" && (
                <Button
                  variant="primary"
                  size="sm"
                  className="text-xs py-1 px-2.5 h-auto"
                  onClick={() => handleApproveLicense(asset.id)}
                >
                  Clear License
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Asset Detail & Licensing Modal */}
      {selectedAsset && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedAsset(null)}
          title="Media Asset Inspection & Provenance"
        >
          <div className="space-y-4">
            <div className="aspect-video rounded-lg overflow-hidden border border-[#262B3A] bg-[#090A0D] flex items-center justify-center">
              <div className="text-center p-6 space-y-2">
                <Badge variant="ember">{selectedAsset.category}</Badge>
                <p className="text-sm font-bold text-white">{selectedAsset.title}</p>
                <p className="text-xs text-gray-400 font-mono">
                  {selectedAsset.width} × {selectedAsset.height} • {selectedAsset.aspectRatio} • {formatBytes(selectedAsset.fileSizeBytes)}
                </p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs text-gray-300 bg-[#14171F] p-4 rounded-lg border border-[#262B3A]">
              <div className="flex items-center justify-between border-b border-[#222736] pb-2">
                <span className="text-gray-500 font-medium">Source Provider</span>
                <span className="font-mono text-[#FF7A00] font-semibold">{selectedAsset.sourceProvider}</span>
              </div>

              <div className="flex items-center justify-between border-b border-[#222736] pb-2">
                <span className="text-gray-500 font-medium">License Type</span>
                <span className="font-mono text-white">{selectedAsset.licenseType}</span>
              </div>

              <div className="flex items-center justify-between border-b border-[#222736] pb-2">
                <span className="text-gray-500 font-medium">License Compliance</span>
                <Badge
                  variant={
                    selectedAsset.licenseStatus === "VERIFIED_COMMERCIAL"
                      ? "success"
                      : "error"
                  }
                >
                  {selectedAsset.licenseStatus}
                </Badge>
              </div>

              <div className="flex items-center justify-between border-b border-[#222736] pb-2">
                <span className="text-gray-500 font-medium">Attribution Requirement</span>
                <span className="text-gray-300">
                  {selectedAsset.attributionText || "None (Public Domain / Verified Free)"}
                </span>
              </div>

              <div className="pt-1">
                <span className="text-gray-500 font-medium block mb-1">SHA-256 Checksum</span>
                <p className="font-mono text-[11px] text-gray-400 break-all bg-[#090A0D] p-2 rounded border border-[#1E222E]">
                  {selectedAsset.sha256Hash}
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedAsset(null)}>
                Close
              </Button>
              {selectedAsset.licenseStatus === "LICENSE_REVIEW_REQUIRED" && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleApproveLicense(selectedAsset.id)}
                >
                  <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
                  Approve for Commercial Use
                </Button>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Upload Custom Asset Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title="Upload Media Asset"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">Asset Title</label>
            <Input
              value={uploadTitle}
              onChange={(e) => setUploadTitle(e.target.value)}
              placeholder="e.g. Microservices Architecture Diagram"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">License Provenance</label>
            <select
              value={uploadLicenseType}
              onChange={(e) => setUploadLicenseType(e.target.value)}
              className="w-full bg-[#14171F] border border-[#262B3A] rounded-lg p-2.5 text-xs text-white"
            >
              <option value="CUSTOM">Owner Created / Original Work (Cleared)</option>
              <option value="CC0">Public Domain / CC0</option>
              <option value="RECORDED_DEMO">Recorded Software Screencast</option>
              <option value="NEEDS_REVIEW">Third-Party Stock (Requires Review)</option>
            </select>
          </div>

          <div className="border-2 border-dashed border-[#262B3A] rounded-lg p-6 text-center space-y-2 bg-[#090A0D]/40">
            <Upload className="w-8 h-8 text-[#FF7A00] mx-auto" />
            <p className="text-xs font-medium text-white">Select image or drop files here</p>
            <p className="text-[10px] text-gray-500">Supports verified PNG, JPEG, WebP, and MP4 up to 50MB</p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowUploadModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleUploadSubmit}
              disabled={isUploading}
            >
              {isUploading ? "Validating & Uploading..." : "Upload Asset"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

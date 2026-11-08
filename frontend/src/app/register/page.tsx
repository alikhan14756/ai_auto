'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Sparkles, ArrowRight, Lock, Mail, User, AlertCircle, Loader2 } from 'lucide-react';
import { registerWithCredentials } from '@/lib/auth';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Please provide your email and password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must contain at least 8 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    try {
      setIsLoading(true);
      await registerWithCredentials(email, password, fullName);
      router.push('/dashboard');
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during registration.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090A0D] text-[#E0E2EC] flex flex-col justify-center items-center px-4 py-12">
      {/* Brand Header */}
      <div className="w-full max-w-md mb-8 text-center">
        <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-[#FF7A00]/10 border border-[#FF7A00]/25 text-[#FF7A00] text-xs font-semibold mb-4 tracking-wide uppercase">
          <Sparkles className="w-3.5 h-3.5" />
          Autonomous YouTube Production
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
          Create Creator Account
        </h1>
        <p className="text-sm text-[#A0A5B5]">
          Start producing autonomous faceless YouTube content
        </p>
      </div>

      {/* Card Container */}
      <div className="w-full max-w-md bg-[#13151B] border border-white/10 rounded-2xl p-8 shadow-2xl backdrop-blur-sm">
        {error && (
          <div className="mb-6 p-3.5 bg-red-500/10 border border-red-500/25 rounded-xl flex items-start gap-3 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-medium text-[#A0A5B5] uppercase tracking-wider mb-2">
              Full Name
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 w-4 h-4 text-[#606575]" />
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Muhammad Ali"
                className="w-full pl-10 pr-4 py-2.5 bg-[#090A0D] border border-white/10 rounded-xl text-sm text-white placeholder-[#505565] focus:outline-none focus:border-[#FF7A00] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A0A5B5] uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 w-4 h-4 text-[#606575]" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="creator@alibuild.site"
                className="w-full pl-10 pr-4 py-2.5 bg-[#090A0D] border border-white/10 rounded-xl text-sm text-white placeholder-[#505565] focus:outline-none focus:border-[#FF7A00] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A0A5B5] uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 w-4 h-4 text-[#606575]" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className="w-full pl-10 pr-4 py-2.5 bg-[#090A0D] border border-white/10 rounded-xl text-sm text-white placeholder-[#505565] focus:outline-none focus:border-[#FF7A00] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A0A5B5] uppercase tracking-wider mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 w-4 h-4 text-[#606575]" />
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                className="w-full pl-10 pr-4 py-2.5 bg-[#090A0D] border border-white/10 rounded-xl text-sm text-white placeholder-[#505565] focus:outline-none focus:border-[#FF7A00] transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3 px-4 bg-[#FF7A00] hover:bg-[#FF8A1A] active:bg-[#E56E00] text-white font-medium rounded-xl text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-[#FF7A00]/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Registering...
              </>
            ) : (
              <>
                Create Creator Workspace
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-white/5 text-center text-xs text-[#A0A5B5]">
          Already have an account?{' '}
          <Link href="/login" className="text-[#FF7A00] hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { LogIn, Shield } from 'lucide-react';

import { AppShell } from '@/components/app-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';
import { storeTokens } from '@/lib/auth';
import { useSessionStore } from '@/stores/use-session-store';

export default function AuthPage() {
  const router = useRouter();
  const setSessionTokens = useSessionStore((state) => state.setTokens);
  const [loginEmail, setLoginEmail] = useState('engineer@aegisops.ai');
  const [password, setPassword] = useState('ChangeMe123!');
  const [registerEmail, setRegisterEmail] = useState('new.engineer@aegisops.ai');
  const [registerPassword, setRegisterPassword] = useState('ChangeMe123!');
  const [message, setMessage] = useState<string | null>(null);

  const loginMutation = useMutation({
    mutationFn: () => api.login({ email: loginEmail, password }),
    onSuccess: ({ access_token, refresh_token }) => {
      storeTokens(access_token, refresh_token);
      setSessionTokens(access_token, refresh_token);
      setMessage('Logged in and session stored locally.');
      router.push('/incidents');
    },
    onError: (error: Error) => setMessage(error.message),
  });

  const registerMutation = useMutation({
    mutationFn: () => api.register({ email: registerEmail, password: registerPassword }),
    onSuccess: ({ access_token, refresh_token }) => {
      storeTokens(access_token, refresh_token);
      setSessionTokens(access_token, refresh_token);
      setMessage('Registered and authenticated successfully.');
      router.push('/incidents');
    },
    onError: (error: Error) => setMessage(error.message),
  });

  return (
    <AppShell
      title="Identity"
      description="JWT login, refresh-session rotation, and optional GitHub OAuth flow backed by the API gateway."
    >
      <div className="grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <Badge className="w-fit border-cyan-400/20 bg-cyan-400/10 text-cyan-200">Auth flow</Badge>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Shield className="h-5 w-5 text-cyan-300" />
              Session login
            </CardTitle>
            <CardDescription>Use your API gateway credentials or GitHub OAuth code.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-slate-400">Stored locally</p>
              <p className="mt-1 font-medium text-white">`access_token` + `refresh_token`</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-slate-400">Gateway endpoints</p>
              <p className="mt-1 font-medium text-white">register, login, refresh, logout</p>
            </div>
            <p className="text-cyan-200">{message ?? 'No action taken yet.'}</p>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <LogIn className="h-5 w-5 text-cyan-300" />
              Authentication panel
            </CardTitle>
            <CardDescription>Switch between login and register without leaving the page.</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login">
              <TabsList className="mb-4 w-full justify-start">
                <TabsTrigger value="login">Login</TabsTrigger>
                <TabsTrigger value="register">Register</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <Input id="login-email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Password</Label>
                    <Input id="login-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
                  </div>
                  <Button className="w-full" onClick={() => loginMutation.mutate()} disabled={loginMutation.isPending}>
                    {loginMutation.isPending ? 'Signing in...' : 'Sign in'}
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="register">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-email">Email</Label>
                    <Input id="register-email" value={registerEmail} onChange={(event) => setRegisterEmail(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password">Password</Label>
                    <Input id="register-password" type="password" value={registerPassword} onChange={(event) => setRegisterPassword(event.target.value)} />
                  </div>
                  <Button className="w-full" onClick={() => registerMutation.mutate()} disabled={registerMutation.isPending}>
                    {registerMutation.isPending ? 'Creating account...' : 'Create account'}
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

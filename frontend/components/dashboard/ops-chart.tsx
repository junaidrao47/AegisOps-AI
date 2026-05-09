'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const data = [
  { name: 'Mon', errors: 18, latency: 620 },
  { name: 'Tue', errors: 14, latency: 540 },
  { name: 'Wed', errors: 21, latency: 700 },
  { name: 'Thu', errors: 11, latency: 430 },
  { name: 'Fri', errors: 9, latency: 380 },
  { name: 'Sat', errors: 7, latency: 330 },
];

export function OpsChart() {
  return (
    <div className="h-[320px] w-full rounded-3xl border border-white/10 bg-white/5 p-5">
      <div className="mb-4">
        <p className="text-sm text-slate-400">Operational trend</p>
        <h3 className="text-xl font-semibold text-white">Incident pressure and latency</h3>
      </div>
      <ResponsiveContainer width="100%" height="82%">
        <LineChart data={data}>
          <XAxis dataKey="name" stroke="#94a3b8" tickLine={false} axisLine={false} />
          <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
          <Line type="monotone" dataKey="errors" stroke="#22d3ee" strokeWidth={3} dot={false} />
          <Line type="monotone" dataKey="latency" stroke="#f59e0b" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

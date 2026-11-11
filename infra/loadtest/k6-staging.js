// Teste de carga — alvo: 1000 usuários simultâneos navegando.
//
//   k6 run -e BASE_URL=https://homolog.exemplo.com.br infra/loadtest/k6-staging.js
//
// Para medir o BACKEND (e não o rate-limit), em homologação:
//   - .env: RATELIMIT_ENABLE=False  (e recriar o web)
//   - nginx: o limite por IP (20 r/s) bloqueia um gerador de carga de 1 IP;
//     rode o k6 de várias máquinas ou eleve temporariamente `zone=api` em
//     infra/nginx/nginx.conf.
// Opcional (cenário logado): -e USER_EMAIL=... -e USER_PASSWORD=...
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL;
const EMAIL = __ENV.USER_EMAIL;
const PASSWORD = __ENV.USER_PASSWORD;

export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-vus',
      stages: [
        { duration: '2m', target: 250 },
        { duration: '3m', target: 1000 },   // sobe até 1000 VUs
        { duration: '10m', target: 1000 },  // sustenta
        { duration: '2m', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],          // < 1% de erro
    http_req_duration: ['p(95)<800'],        // p95 < 800 ms
    'http_req_duration{group:::login}': ['p(95)<1200'],
  },
};

export function setup() {
  if (!EMAIL) return { token: null };
  const r = http.post(`${BASE}/api/auth/login`, JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } });
  return { token: r.status === 200 ? r.json('access') : null };
}

export default function (data) {
  // Navegação pública (maioria do tráfego): catálogo, produtos, equipe.
  const pages = [
    '/api/services/list-services',
    '/api/products/list-public-products',
    '/api/employees/team',
    '/api/average-ratings/all',
  ];
  for (const p of pages) {
    const r = http.get(`${BASE}${p}`);
    check(r, { [`${p} 200`]: (x) => x.status === 200 });
    sleep(Math.random() * 3 + 1);           // "tempo de leitura" 1–4 s
  }

  // Parte dos usuários está logada.
  if (data.token && Math.random() < 0.3) {
    const h = { headers: { Authorization: `Bearer ${data.token}` } };
    const me = http.get(`${BASE}/api/auth/me`, h);
    check(me, { 'me 200': (x) => x.status === 200 });
    const n = http.get(`${BASE}/api/notifications/unread-count/`, h);
    check(n, { 'unread-count 200': (x) => x.status === 200 });
    sleep(Math.random() * 3 + 1);
  }
}
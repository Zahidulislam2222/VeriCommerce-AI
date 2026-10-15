export const appConfig = Object.freeze({
  route: { home: '/', workspace: '/workspace', core: '/engine' },
  core: {
    base: '/api',
    requestTimeoutSeconds: 90,
    jobTimeoutSeconds: 120,
    pollSeconds: 1,
    importMaxBytes: 262144,
    queryMaxLength: 500,
    approveSuffix: '/approve',
    exportSuffix: '/export',
    paths: { session: '/session', overview: '/overview', products: '/products', sources: '/sources',
      drafts: '/drafts', audit: '/audit', search: '/search', answers: '/answers',
      ingestions: '/ingestions', jobs: '/jobs', evaluations: '/evaluations', graph: '/graph' },
  },
  media: {
    hero: '/images/hero-headphones.webp',
    heroVideo: '/videos/hero-headphones.mp4',
  },
  motion: {
    revealSeconds: 0.65,
    revealDistance: 24,
    staggerSeconds: 0.09,
    smoothScrollSeconds: 1.1,
    hoverSeconds: 0.25,
    heroSeconds: 1,
    introDelay: 0.25,
    footnoteDelay: 0.35,
    floatDelay: 0.7,
    springStiffness: 100,
    springDamping: 30,
    ease: [0.22, 1, 0.36, 1] as const,
  },
  storage: { approvals: 'vericommerce.demo.approvals.v1' },
  noticeSeconds: 4,
  assetVideoEnabled: import.meta.env.VITE_HERO_VIDEO === 'true',
});

if (!['true', 'false', undefined].includes(import.meta.env.VITE_HERO_VIDEO)) {
  throw new Error('VITE_HERO_VIDEO must be true or false.');
}

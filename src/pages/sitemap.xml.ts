import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

// Generated at build time so new blog posts are always included.
const staticPages: { path: string; changefreq: string; priority: string }[] = [
  { path: '/', changefreq: 'weekly', priority: '1.0' },
  { path: '/resume', changefreq: 'monthly', priority: '0.9' },
  { path: '/nick-ai', changefreq: 'weekly', priority: '0.8' },
  { path: '/blog', changefreq: 'weekly', priority: '0.8' },
  { path: '/illustrations', changefreq: 'monthly', priority: '0.7' },
  { path: '/atomic-docs', changefreq: 'monthly', priority: '0.6' },
  { path: '/fonts', changefreq: 'monthly', priority: '0.6' },
];

const toDate = (d: Date) => d.toISOString().split('T')[0];

export const GET: APIRoute = async ({ site }) => {
  const base = (site?.href ?? 'https://nickberens.me/').replace(/\/$/, '');
  const posts = (await getCollection('blog')).sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf()
  );

  const urls = [
    ...staticPages.map(
      (p) => `  <url>
    <loc>${base}${p.path}</loc>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`
    ),
    ...posts.map(
      (post) => `  <url>
    <loc>${base}/blog/${post.slug}</loc>
    <lastmod>${toDate(post.data.updatedDate ?? post.data.pubDate)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>`
    ),
  ];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>
`;

  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};

import data from './data/public-pages.json';

export function isPublicPath(path: string) {
  return data.pages.some((page) => page.path === path);
}

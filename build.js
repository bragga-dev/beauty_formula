/**
 * build.js — compila o Tailwind e injeta os estilos inline (juice),
 * preservando as tags Jinja. Uso: npm run build
 *
 * base.src.html  →  base.html
 */
const { execSync } = require('node:child_process');
const fs = require('node:fs');
const juice = require('juice');

fs.mkdirSync('dist', { recursive: true });
execSync('npx tailwindcss -c tailwind.config.js -i email.css -o dist/email.css', { stdio: 'inherit' });

// remove comentários do CSS: no xmlMode, qualquer "<tag>" dentro do <style> vira elemento
const css = fs.readFileSync('dist/email.css', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
let html = fs.readFileSync('base.src.html', 'utf8').replace('<!-- @tailwind-css -->', `<style>${css}</style>`);

// Protege Jinja: {% ... %} e {{ ... }} viram tokens de texto durante o inline.
const stash = [];
html = html.replace(/\{%[\s\S]*?%\}|\{\{[\s\S]*?\}\}/g, (m) => {
  stash.push(m);
  return `__JINJA_${stash.length - 1}__`;
});

html = juice(html, {
  removeStyleTags: false,     // mantém <style> p/ media queries e classes dos templates filhos
  preserveImportant: true,
  preserveMediaQueries: true,
  preserveFontFaces: true,
  applyWidthAttributes: false,
  xmlMode: true,              // não mexe na estrutura do <head> com os blocks Jinja
});

html = html.replace(/__JINJA_(\d+)__/g, (_, i) => stash[Number(i)]);
fs.writeFileSync('base.html', html);
console.log(`base.html gerado (${(html.length / 1024).toFixed(1)} KB)`);

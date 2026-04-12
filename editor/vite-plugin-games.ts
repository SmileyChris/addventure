import { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';

export function gamesPlugin(): Plugin {
  // Resolve the games directory relative to the project root (one level up from editor/)
  const gamesDir = path.resolve(__dirname, '..', 'games');

  return {
    name: 'addventure-games',
    configureServer(server) {
      // GET /api/games — list game directories or read a specific game
      // Returns: { games: [{ name: string, files: string[] }] } or { files: Record<string, string> }
      server.middlewares.use('/api/games', (req, res, next) => {
        if (req.method !== 'GET') return next();
        const url = new URL(req.url!, `http://${req.headers.host}`);
        const gameName = url.pathname.replace(/^\//, '');

        if (!gameName) {
          // List all game directories
          try {
            const entries = fs.readdirSync(gamesDir, { withFileTypes: true });
            const games = entries
              .filter(e => e.isDirectory())
              .filter(e => fs.existsSync(path.join(gamesDir, e.name, 'index.md')))
              .map(e => ({
                name: e.name,
                files: fs.readdirSync(path.join(gamesDir, e.name))
                  .filter(f => f.endsWith('.md')),
              }));
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ games }));
          } catch (err) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: String(err) }));
          }
        } else {
          // Read all .md files from a specific game directory
          const gameDir = path.join(gamesDir, gameName);
          if (!fs.existsSync(gameDir)) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: 'Game not found' }));
            return;
          }
          try {
            const mdFiles = fs.readdirSync(gameDir).filter(f => f.endsWith('.md'));
            const files: Record<string, string> = {};
            for (const f of mdFiles) {
              files[f] = fs.readFileSync(path.join(gameDir, f), 'utf-8');
            }
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ files }));
          } catch (err) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: String(err) }));
          }
        }
      });

      // PUT /api/save/:name — save all .md files for a game
      // Body: { files: Record<string, string> }
      server.middlewares.use('/api/save', (req, res, next) => {
        if (req.method !== 'PUT') return next();
        const url = new URL(req.url!, `http://${req.headers.host}`);
        const gameName = url.pathname.replace(/^\//, '');
        if (!gameName) {
          res.statusCode = 400;
          res.end(JSON.stringify({ error: 'Game name required' }));
          return;
        }

        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
          try {
            const { files } = JSON.parse(body) as { files: Record<string, string> };
            const gameDir = path.join(gamesDir, gameName);

            // Create directory if it doesn't exist
            if (!fs.existsSync(gameDir)) {
              fs.mkdirSync(gameDir, { recursive: true });
            }

            // Remove old .md files that aren't in the new set
            const existing = fs.readdirSync(gameDir).filter(f => f.endsWith('.md'));
            for (const f of existing) {
              if (!files[f]) {
                fs.unlinkSync(path.join(gameDir, f));
              }
            }

            // Write new files
            for (const [filename, content] of Object.entries(files)) {
              fs.writeFileSync(path.join(gameDir, filename), content, 'utf-8');
            }

            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ ok: true }));
          } catch (err) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: String(err) }));
          }
        });
      });
    },
  };
}

// Freier Nachbau-Server (flying-squid) zum Ausprobieren der Brücke ohne Mojangs Server.
// Er ist stark vereinfacht: keine Monster-KI, kein Craften am Server, keine Fortschritte.
// Für Messungen dient der offizielle Server (siehe docs/MINECRAFT.md).
// Aufruf: node testserver.js [Port]

'use strict'

const mcServer = require('flying-squid')

mcServer.createMCServer({
  motd: 'HekmatKI Testserver',
  port: Number(process.argv[2] || 25565),
  'max-players': 4,
  'online-mode': false,
  logging: false,
  gameMode: 0,
  difficulty: 1,
  generation: { name: 'diamond_square', options: { worldHeight: 80 } },
  kickTimeout: 10000,
  plugins: {},
  modpe: false,
  'view-distance': 4,
  'player-list-text': { header: 'HekmatKI', footer: 'Test' },
  'everybody-op': true,
  'max-entities': 100,
  version: '1.20.4'
})

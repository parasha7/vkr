/**
 * LaserControl — расширение mBlock 5 (Extension Builder, live mode).
 * Назначение: сформировать JSON-команды верхнего уровня и передать их
 * контроллеру-посреднику, который преобразует их в G-код GRBL.
 *
 * Важно: использованы API mBlock 5 Extension Builder (app, device, block):
 *   https://support.makeblock.com/hc/en-us/articles/15236766560791-Extension-APIs
 * Фактическая совместимость с установленной сборкой mBlock проверяется
 * техническим тестом (Тесты/01_технический_тест_LaserControl.md).
 */

const TEXT_ENCODER = typeof TextEncoder !== 'undefined' ? new TextEncoder() : null;

function toBytes(text) {
    if (TEXT_ENCODER) {
        return Array.from(TEXT_ENCODER.encode(text));
    }
    const bytes = [];
    for (let i = 0; i < text.length; i += 1) {
        bytes.push(text.charCodeAt(i) & 0xff);
    }
    return bytes;
}

function number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

module.exports = {
    extensionName: 'lasercontrol',

    blocks: [
        {
            opcode: 'connect',
            blockType: 'command',
            text: 'подключиться к граверу',
            arguments: {}
        },
        {
            opcode: 'home',
            blockType: 'command',
            text: 'вернуться в ноль',
            arguments: {}
        },
        {
            opcode: 'moveAbsolute',
            blockType: 'command',
            text: 'переместить в точку X [X] Y [Y]',
            arguments: {
                X: { type: 'number', defaultValue: 10 },
                Y: { type: 'number', defaultValue: 10 }
            }
        },
        {
            opcode: 'moveRelative',
            blockType: 'command',
            text: 'сдвинуть на X [X] Y [Y]',
            arguments: {
                X: { type: 'number', defaultValue: 0 },
                Y: { type: 'number', defaultValue: 10 }
            }
        },
        {
            opcode: 'laser',
            blockType: 'command',
            text: 'лазер [STATE]',
            arguments: {
                STATE: {
                    type: 'string',
                    defaultValue: 'off',
                    menu: { off: 'выключить', on: 'включить' }
                }
            }
        },
        {
            opcode: 'power',
            blockType: 'command',
            text: 'установить мощность [VALUE] %',
            arguments: {
                VALUE: { type: 'number', defaultValue: 20, min: 0, max: 100 }
            }
        },
        {
            opcode: 'feedrate',
            blockType: 'command',
            text: 'установить скорость [VALUE] мм/мин',
            arguments: {
                VALUE: { type: 'number', defaultValue: 1000, min: 1, max: 10000 }
            }
        },
        {
            opcode: 'drawLine',
            blockType: 'command',
            text: 'линия из [X1] [Y1] в [X2] [Y2]',
            arguments: {
                X1: { type: 'number', defaultValue: 10 },
                Y1: { type: 'number', defaultValue: 10 },
                X2: { type: 'number', defaultValue: 60 },
                Y2: { type: 'number', defaultValue: 10 }
            }
        },
        {
            opcode: 'drawRect',
            blockType: 'command',
            text: 'прямоугольник X [X] Y [Y] ширина [W] высота [H]',
            arguments: {
                X: { type: 'number', defaultValue: 20 },
                Y: { type: 'number', defaultValue: 20 },
                W: { type: 'number', defaultValue: 20 },
                H: { type: 'number', defaultValue: 10 }
            }
        },
        {
            opcode: 'drawCircle',
            blockType: 'command',
            text: 'окружность X [X] Y [Y] радиус [R]',
            arguments: {
                X: { type: 'number', defaultValue: 65 },
                Y: { type: 'number', defaultValue: 65 },
                R: { type: 'number', defaultValue: 15 }
            }
        },
        {
            opcode: 'delay',
            blockType: 'command',
            text: 'пауза [MS] мс',
            arguments: {
                MS: { type: 'number', defaultValue: 1000 }
            }
        },
        {
            opcode: 'emergencyStop',
            blockType: 'command',
            text: 'АВАРИЙНАЯ ОСТАНОВКА',
            arguments: {}
        },
        {
            opcode: 'status',
            blockType: 'reporter',
            text: 'состояние гравера',
            arguments: {}
        }
    ],

    onLoad(app, /* target */) {
        app.log('LaserControl 0.1.0 loaded. Проверьте COM-порт и OD≥4 для 445–455 нм.');
    },

    onStopAll(app, device) {
        // Красная кнопка mBlock / блок «остановить всё»: лазер выключается всегда.
        this.sendCommand(app, device, { cmd: 'emergency_stop' });
    },

    onRead(app, device) {
        const text = device.readText(false);
        if (text && text.trim()) {
            app.log('LaserControl <- ' + text.trim());
        }
    },

    sendCommand(app, device, payload) {
        const line = JSON.stringify(payload) + '\n';
        app.log('LaserControl -> ' + line.trim());
        if (device && typeof device.writeRaw === 'function') {
            device.writeRaw(toBytes(line));
        } else if (device && typeof device.writeText === 'function') {
            device.writeText(line);
        } else {
            app.warn('Последовательный порт недоступен: проверьте подключение устройства в mBlock.');
        }
    },

    onRun(args, app, device, block) {
        switch (block.opcode) {
            case 'connect':
                return this.sendCommand(app, device, { cmd: 'connect' });
            case 'home':
                return this.sendCommand(app, device, { cmd: 'home' });
            case 'moveAbsolute':
                return this.sendCommand(app, device, {
                    cmd: 'move',
                    params: { x: number(args.X), y: number(args.Y), abs: true }
                });
            case 'moveRelative':
                return this.sendCommand(app, device, {
                    cmd: 'move',
                    params: { x: number(args.X), y: number(args.Y), abs: false }
                });
            case 'laser':
                return this.sendCommand(app, device, {
                    cmd: 'laser',
                    params: { state: args.STATE === 'on' ? 'on' : 'off' }
                });
            case 'power':
                return this.sendCommand(app, device, {
                    cmd: 'power',
                    params: { value: number(args.VALUE, 20) }
                });
            case 'feedrate':
                return this.sendCommand(app, device, {
                    cmd: 'feedrate',
                    params: { value: number(args.VALUE, 1000) }
                });
            case 'drawLine':
                return this.sendCommand(app, device, {
                    cmd: 'line',
                    params: {
                        x1: number(args.X1), y1: number(args.Y1),
                        x2: number(args.X2), y2: number(args.Y2)
                    }
                });
            case 'drawRect':
                return this.sendCommand(app, device, {
                    cmd: 'rect',
                    params: {
                        x: number(args.X), y: number(args.Y),
                        w: number(args.W), h: number(args.H)
                    }
                });
            case 'drawCircle':
                return this.sendCommand(app, device, {
                    cmd: 'circle',
                    params: {
                        x: number(args.X), y: number(args.Y), r: number(args.R)
                    }
                });
            case 'delay':
                return this.sendCommand(app, device, {
                    cmd: 'delay',
                    params: { ms: number(args.MS, 1000) }
                });
            case 'emergencyStop':
                return this.sendCommand(app, device, { cmd: 'emergency_stop' });
            case 'status':
                return this.sendCommand(app, device, { cmd: 'status' });
            default:
                app.warn('Неизвестный блок LaserControl: ' + block.opcode);
                return undefined;
        }
    }
};

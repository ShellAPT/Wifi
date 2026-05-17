const fs = require('fs');

const prefixes = [
  '032', '033', '034', '035', '036', '037', '038', '039',
  '096', '097', '098',
  '070', '076', '077', '078', '079',
  '090', '093',
  '081', '082', '083', '084', '085',
  '088', '091', '094',
  '056', '058',
];

const TOTAL = 10_000_000;

const stream = fs.createWriteStream('1.txt', {
  flags: 'w',
  encoding: 'utf8',
  highWaterMark: 1024 * 1024 * 32,
});

let generated = 0;
let paused = false;

function random7() {
  return (Math.random() * 10_000_000) | 0;
}

function generateChunk(size) {
  let out = '';
  let i = 0;

  while (i < size) {
    const prefix = prefixes[(Math.random() * prefixes.length) | 0];

    let n = random7();

    if (n < 10) {
      out += prefix + '000000' + n + '\n';
    } else if (n < 100) {
      out += prefix + '00000' + n + '\n';
    } else if (n < 1000) {
      out += prefix + '0000' + n + '\n';
    } else if (n < 10000) {
      out += prefix + '000' + n + '\n';
    } else if (n < 100000) {
      out += prefix + '00' + n + '\n';
    } else if (n < 1000000) {
      out += prefix + '0' + n + '\n';
    } else {
      out += prefix + n + '\n';
    }

    i++;
  }

  return out;
}

function writeLoop() {
  while (!paused && generated < TOTAL) {
    const remain = TOTAL - generated;

    const batch =
      remain > 200000
        ? 200000
        : remain;

    const chunk = generateChunk(batch);

    generated += batch;

    if (
      generated % 1000000 === 0 ||
      generated === TOTAL
    ) {
      const mb = (generated * 11 / 1024 / 1024).toFixed(1);

      process.stdout.write(
        `\rGenerated: ${generated.toLocaleString()} | ~${mb} MB`
      );
    }

    paused = !stream.write(chunk);
  }

  if (generated >= TOTAL) {
    stream.end();
  }
}

stream.on('drain', () => {
  paused = false;
  setImmediate(writeLoop);
});

stream.on('finish', () => {
  console.log('\n✅ Finished');
});

stream.on('error', console.error);

writeLoop();
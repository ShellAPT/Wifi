const fs = require('fs');

const DAYS = [
  '01','02','03','04','05','06','07',
  '08','09','10','11','12','13','14',
  '15','16','17','18','19','20','21',
  '22','23','24','25','26','27','28'
];

const MONTHS = [
  '01','02','03','04','05','06',
  '07','08','09','10','11','12'
];

const TOTAL = 10_000_000;

const OUTPUT = 'birthdays.txt';

const stream = fs.createWriteStream(OUTPUT, {
  flags: 'w',
  encoding: 'utf8',
  highWaterMark: 1024 * 1024 * 32,
});

let generated = 0;
let paused = false;

function generateChunk(count) {
  let out = '';
  let i = 0;

  while (i < count) {
    const day = DAYS[(Math.random() * 28) | 0];
    const month = MONTHS[(Math.random() * 12) | 0];
    const year = 1960 + ((Math.random() * 121) | 0);

    out += day + month + year + '\n';

    i++;
  }

  return out;
}

function writeLoop() {
  while (!paused && generated < TOTAL) {
    const remain = TOTAL - generated;

    const batch =
      remain > 300000
        ? 300000
        : remain;

    const chunk = generateChunk(batch);

    generated += batch;

    if (
      generated % 1000000 === 0 ||
      generated === TOTAL
    ) {
      const mb = ((generated * 9) / 1024 / 1024).toFixed(1);

      process.stdout.write(
        `\rWritten: ${generated.toLocaleString()} | ~${mb} MB`
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
  console.log(`\n✅ Saved to ${OUTPUT}`);
});

stream.on('error', console.error);

writeLoop();
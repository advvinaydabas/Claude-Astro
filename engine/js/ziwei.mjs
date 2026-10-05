// Canonical iztro run. Usage: node ziwei.mjs '<json args>'
// args: {solarDate, timeIndex, gender, fixLeap, lang, horoscopeDates: [...]}
import { astro } from 'iztro';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pkg = require('iztro/package.json');
const args = JSON.parse(process.argv[2]);
const a = astro.bySolar(args.solarDate, args.timeIndex, args.gender, args.fixLeap, args.lang);
const out = JSON.parse(JSON.stringify(a));
out.iztro_version = pkg.version;
out.horoscopes = {};
for (const d of args.horoscopeDates || []) {
  const h = a.horoscope(d);
  out.horoscopes[d] = {
    lunarDate: h.lunarDate, solarDate: h.solarDate,
    decadal: { index: h.decadal.index, heavenlyStem: h.decadal.heavenlyStem, earthlyBranch: h.decadal.earthlyBranch, mutagen: h.decadal.mutagen },
    yearly: { index: h.yearly.index, heavenlyStem: h.yearly.heavenlyStem, earthlyBranch: h.yearly.earthlyBranch, mutagen: h.yearly.mutagen },
    age: { index: h.age.index, nominalAge: h.age.nominalAge },
  };
}
console.log(JSON.stringify(out));

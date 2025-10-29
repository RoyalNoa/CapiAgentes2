const fetch = global.fetch;
const BALANCE_TOLERANCE = 0.4;
(async () => {
  const res = await fetch("http://localhost:3000/api/maps/sucursales");
  const data = await res.json();
  const map = new Map(data.map(rec => [rec.sucursal_id, rec]));
  const routes = [
    ['SUC-395', 'SUC-423', 'SUC-408', 'SUC-417'],
    ['SUC-406', 'SUC-405', 'SUC-407', 'SUC-402'],
    ['SUC-420', 'SUC-437', 'SUC-435', 'SUC-430'],
    ['SUC-398', 'SUC-377', 'SUC-432', 'SUC-382'],
    ['SUC-413', 'SUC-363', 'SUC-410', 'SUC-433'],
  ];
  routes.forEach((route, idx) => {
    route.forEach(id => {
      const rec = map.get(id);
      if (rec) {
        const caja = Number(rec.caja_teorica_sucursal ?? 0);
        const saldo = Number(rec.saldo_total_sucursal ?? 0);
        const delta = caja !== 0 ? (saldo - caja) / Math.abs(caja) : null;
        console.log(idx + 1, id, delta != null ? delta.toFixed(3) : 'null');
      }
    });
  });
})();

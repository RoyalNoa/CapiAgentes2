const fetch = global.fetch;
(async () => {
  const res = await fetch("http://localhost:3000/api/maps/sucursales");
  const data = await res.json();
  const sanitized = data.filter(rec => Number.isFinite(rec.latitud) && Number.isFinite(rec.longitud));
  const ids = new Set(sanitized.map(rec => rec.sucursal_id));
  const routes = [
    ['SUC-395', 'SUC-423', 'SUC-408', 'SUC-417'],
    ['SUC-406', 'SUC-405', 'SUC-407', 'SUC-402'],
    ['SUC-420', 'SUC-437', 'SUC-435', 'SUC-430'],
    ['SUC-398', 'SUC-377', 'SUC-432', 'SUC-382'],
    ['SUC-413', 'SUC-363', 'SUC-410', 'SUC-433'],
  ];
  routes.forEach((route, idx) => {
    const missing = route.filter(id => !ids.has(id));
    if (missing.length) {
      console.log('Route', idx + 1, 'missing', missing);
    }
  });
})();

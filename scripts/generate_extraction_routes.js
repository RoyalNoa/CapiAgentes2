#!/usr/bin/env node

/**
 * Generates optimized return routes for cash trucks based on the latest
 * sucursal balances. The script:
 *  - reads sucursal data from `sucursales.json`
 *  - derives the last visited branch for each truck from the deposit plan
 *  - assigns every branch with saldo > +40% to exactly one truck
 *    by incrementally inserting it where it minimally increases distance
 *  - writes the resulting paths to:
 *      * `docs/caudales/rutas_retorno_optimizadas.csv`
 *      * `Frontend/src/app/pages/map/google/predefinedExtractionRoutes.json`
 */

const fs = require('fs');
const path = require('path');

const SURPLUS_THRESHOLD = 0.4;
const SIMULATION_TRUCK_COUNT = 5;
const EARTH_RADIUS_METERS = 6371000;

const PREDEFINED_DEPOSIT_ROUTES = [
  ['SUC-395', 'SUC-423', 'SUC-408', 'SUC-417'],
  ['SUC-406', 'SUC-405', 'SUC-407', 'SUC-402'],
  ['SUC-420', 'SUC-437', 'SUC-435', 'SUC-430'],
  ['SUC-398', 'SUC-377', 'SUC-432', 'SUC-382'],
  ['SUC-413', 'SUC-363', 'SUC-410', 'SUC-433'],
];

const VESSEL_ID = 'BOVEDA';
const VAULT_COORDS = { latitud: -34.6073508, longitud: -58.3722956 };

function toRadians(value) {
  return (value * Math.PI) / 180;
}

function getDistanceMeters(a, b) {
  const lat1 = toRadians(a.latitud);
  const lon1 = toRadians(a.longitud);
  const lat2 = toRadians(b.latitud);
  const lon2 = toRadians(b.longitud);
  const dLat = lat2 - lat1;
  const dLon = lon2 - lon1;

  const hav =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(hav), Math.sqrt(1 - hav));
  return EARTH_RADIUS_METERS * c;
}

function ensureLatLng(record) {
  return {
    latitud: Number(record.latitud),
    longitud: Number(record.longitud),
  };
}

function coverageRatio(record) {
  const caja = Number(record.caja_teorica_sucursal);
  const saldo = Number(record.saldo_total_sucursal);
  if (!Number.isFinite(caja) || caja === 0) {
    return null;
  }
  return (saldo - caja) / caja;
}

function loadSucursales() {
  const sourcePath = path.resolve('sucursales.json');
  const raw = fs.readFileSync(sourcePath, 'utf8');
  const records = JSON.parse(raw);
  return records.filter(
    (record) =>
      Number.isFinite(Number(record.latitud)) &&
      Number.isFinite(Number(record.longitud))
  );
}

function buildDepositSummary(records) {
  const branchesById = new Map(records.map((record) => [record.sucursal_id, record]));
  const deficitRecords = records.filter((record) => {
    const ratio = coverageRatio(record);
    return ratio !== null && ratio <= -SURPLUS_THRESHOLD;
  });

  const deficitMap = new Map(deficitRecords.map((record) => [record.sucursal_id, record]));

  const plans = PREDEFINED_DEPOSIT_ROUTES.map((routeIds) => {
    const branches = [];
    routeIds.forEach((id) => {
      const branch = deficitMap.get(id) ?? branchesById.get(id);
      if (branch && deficitMap.has(branch.sucursal_id)) {
        branches.push(branch);
        deficitMap.delete(branch.sucursal_id);
      }
    });
    let current = branches.length
      ? ensureLatLng(branches[branches.length - 1])
      : ensureLatLng(VAULT_COORDS);
    return { branches, current };
  });

  Array.from(deficitMap.values()).forEach((branch) => {
    const coords = ensureLatLng(branch);
    let bestIndex = 0;
    let bestDist = Infinity;

    plans.forEach((plan, index) => {
      const distance = getDistanceMeters(plan.current, coords);
      if (distance < bestDist) {
        bestIndex = index;
        bestDist = distance;
      }
    });

    plans[bestIndex].branches.push(branch);
    plans[bestIndex].current = coords;
  });

  const endpointsByRoute = new Map();
  plans.forEach((plan, index) => {
    const routeId = `truck-${index + 1}`;
    const lastBranch = plan.branches[plan.branches.length - 1] ?? null;
    endpointsByRoute.set(routeId, lastBranch ? lastBranch.sucursal_id : null);
  });

  return endpointsByRoute;
}

function buildOptimizedRoutes(records) {
  const sucursalById = new Map(records.map((record) => [record.sucursal_id, record]));
  const endpointsByRoute = buildDepositSummary(records);

  const targets = records.filter((record) => {
    const ratio = coverageRatio(record);
    return ratio !== null && ratio > SURPLUS_THRESHOLD;
  });
  const targetIds = new Set(targets.map((record) => record.sucursal_id));

  const routes = Array.from({ length: SIMULATION_TRUCK_COUNT }).map((_, index) => {
    const truckId = `truck-${index + 1}`;
    const startId = endpointsByRoute.get(truckId) ?? VESSEL_ID;
    const startRecord =
      startId === VESSEL_ID
        ? { sucursal_id: VESSEL_ID, sucursal_nombre: 'Boveda Central', ...VAULT_COORDS }
        : sucursalById.get(startId);

    if (!startRecord) {
      throw new Error(`No se pudo encontrar la sucursal ${startId} para ${truckId}`);
    }

    const assigned = [];
    if (targetIds.has(startRecord.sucursal_id)) {
      assigned.push(startRecord.sucursal_id);
    }

    return {
      truckId,
      startId: startRecord.sucursal_id,
      assigned,
    };
  });

  const unassigned = targets
    .map((record) => record.sucursal_id)
    .filter((id) => {
      return !routes.some((route) => route.assigned.includes(id));
    });

  function coordinateOf(id) {
    if (id === VESSEL_ID) {
      return VAULT_COORDS;
    }
    const record = sucursalById.get(id);
    if (!record) {
      throw new Error(`Sucursal ${id} inexistente en datos.`);
    }
    return record;
  }

  function routeSequence(route) {
    const sequence = [route.startId, ...route.assigned, VESSEL_ID];
    return sequence;
  }

  function insertionCost(route, candidateId) {
    const candidateCoords = coordinateOf(candidateId);
    const sequence = routeSequence(route);
    let best = { cost: Infinity, index: 0 };

    for (let i = 0; i < sequence.length - 1; i += 1) {
      const beforeId = sequence[i];
      const afterId = sequence[i + 1];
      const beforeCoords = coordinateOf(beforeId);
      const afterCoords = coordinateOf(afterId);

      const base = getDistanceMeters(beforeCoords, afterCoords);
      const added =
        getDistanceMeters(beforeCoords, candidateCoords) +
        getDistanceMeters(candidateCoords, afterCoords);
      const delta = added - base;

      if (delta < best.cost) {
        best = { cost: delta, index: Math.min(i, route.assigned.length) };
      }
    }

    return best;
  }

  while (unassigned.length) {
    let bestChoice = null;

    unassigned.forEach((candidateId) => {
      routes.forEach((route) => {
        const { cost, index } = insertionCost(route, candidateId);
        if (
          !bestChoice ||
          cost < bestChoice.cost ||
          (cost === bestChoice.cost && route.assigned.length < bestChoice.route.assigned.length)
        ) {
          bestChoice = { route, candidateId, cost, index };
        }
      });
    });

    if (!bestChoice) {
      throw new Error('No se pudo asignar una sucursal restante.');
    }

    bestChoice.route.assigned.splice(bestChoice.index, 0, bestChoice.candidateId);
    unassigned.splice(unassigned.indexOf(bestChoice.candidateId), 1);
  }

  return routes.map((route) => ({
    truckId: route.truckId,
    sequence: [route.startId, ...route.assigned.filter((id, index) => index !== 0 || route.startId !== id)],
  }));
}

function writeCsv(routes, sucursalById) {
  const csvPath = path.resolve('docs/caudales/rutas_retorno_optimizadas.csv');
  const lines = ['camion,orden,sucursal_id,sucursal_nombre,latitud,longitud,ratio'];

  routes.forEach((route) => {
    route.sequence.forEach((id, index) => {
      const record =
        id === VESSEL_ID
          ? { sucursal_id: VESSEL_ID, sucursal_nombre: 'Boveda Central', ...VAULT_COORDS }
          : sucursalById.get(id);
      if (!record) {
        return;
      }
      const ratio = id === VESSEL_ID ? 0 : Number((coverageRatio(record) ?? 0).toFixed(2));
      lines.push(
        [
          route.truckId,
          index,
          record.sucursal_id,
          record.sucursal_nombre,
          record.latitud,
          record.longitud,
          ratio,
        ].join(',')
      );
    });
  });

  fs.writeFileSync(csvPath, `${lines.join('\n')}\n`, 'utf8');
}

function writeJson(routes) {
  const jsonPath = path.resolve(
    'Frontend/src/app/pages/map/google/predefinedExtractionRoutes.json'
  );
  const payload = routes.map((route) => route.sequence);
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function main() {
  const records = loadSucursales();
  const sucursalById = new Map(records.map((record) => [record.sucursal_id, record]));
  const routes = buildOptimizedRoutes(records);

  routes.forEach((route) => route.sequence.push(VESSEL_ID));

  writeCsv(routes, sucursalById);

  const routeDistances = routes.map((route) => {
    let distance = 0;
    for (let i = 0; i < route.sequence.length - 1; i += 1) {
      const from = route.sequence[i];
      const to = route.sequence[i + 1];
      const fromCoords =
        from === VESSEL_ID ? VAULT_COORDS : sucursalById.get(from) ?? VAULT_COORDS;
      const toCoords =
        to === VESSEL_ID ? VAULT_COORDS : sucursalById.get(to) ?? VAULT_COORDS;
      distance += getDistanceMeters(ensureLatLng(fromCoords), ensureLatLng(toCoords));
    }
    return { id: route.truckId, distance };
  });

  const totalDistance = routeDistances.reduce((acc, item) => acc + item.distance, 0);
  routeDistances.forEach((item) => {
    console.log(`${item.id}: ${(item.distance / 1000).toFixed(2)} km`);
  });
  console.log(`Total recorrido: ${(totalDistance / 1000).toFixed(2)} km`);

  routes.forEach((route) => {
    route.sequence.pop(); // remove BOVEDA for json config
  });

  writeJson(routes);
  console.log('Rutas de retiro generadas correctamente.');
}

main();

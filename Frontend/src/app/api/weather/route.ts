import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const OPEN_METEO_ENDPOINT = 'https://api.open-meteo.com/v1/forecast?latitude=-34.6037&longitude=-58.3816&current_weather=true&timezone=America%2FArgentina%2FBuenos_Aires';

const WEATHER_CODE_DESCRIPTIONS: Record<number, string> = {
  0: 'Cielo despejado',
  1: 'Principalmente despejado',
  2: 'Parcialmente nublado',
  3: 'Nublado',
  45: 'Neblina',
  48: 'Neblina con escarcha',
  51: 'Llovizna débil',
  53: 'Llovizna',
  55: 'Llovizna intensa',
  56: 'Llovizna gélida ligera',
  57: 'Llovizna gélida intensa',
  61: 'Lluvia débil',
  63: 'Lluvia',
  65: 'Lluvia intensa',
  66: 'Lluvia helada ligera',
  67: 'Lluvia helada intensa',
  71: 'Nevada ligera',
  73: 'Nevada',
  75: 'Nevada intensa',
  77: 'Aguanieve',
  80: 'Chubascos débiles',
  81: 'Chubascos',
  82: 'Chubascos intensos',
  85: 'Chubascos de nieve ligeros',
  86: 'Chubascos de nieve',
  95: 'Tormenta eléctrica',
  96: 'Tormenta eléctrica con granizo',
  99: 'Tormenta eléctrica severa con granizo',
};

function describeWeather(code: number | null | undefined): string {
  if (code === null || code === undefined || Number.isNaN(code)) {
    return 'Condiciones no disponibles';
  }

  return WEATHER_CODE_DESCRIPTIONS[code] ?? 'Condiciones no disponibles';
}

function formatTemperature(value: number | null | undefined): { raw: number | null; display: string } {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return {
      raw: null,
      display: '---',
    };
  }

  const rounded = Math.round(value);
  return {
    raw: value,
    display: `${rounded}°C`,
  };
}

export async function GET() {
  try {
    const response = await fetch(OPEN_METEO_ENDPOINT, { cache: 'no-store' });
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(`HTTP ${response.status}${body ? `: ${body.slice(0, 200)}` : ''}`);
    }

    const payload = await response.json();
    const currentWeather = payload?.current_weather ?? null;
    const { raw: temperature, display: temperatureFormatted } = formatTemperature(currentWeather?.temperature);
    const condition = describeWeather(currentWeather?.weathercode);

    return NextResponse.json({
      provider: 'open-meteo',
      location: 'CABA · Microcentro',
      condition,
      temperature,
      temperatureFormatted,
      observedAt: currentWeather?.time ?? null,
      windSpeed: currentWeather?.windspeed ?? null,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      {
        error: 'No se pudo recuperar el clima actual.',
        message,
      },
      { status: 502 },
    );
  }
}

const MAIN_ROUTE = '/pages/';

export const ROUTES = [
  {
    name: 'Home',
    to: `${MAIN_ROUTE}home`,
    icon: '/home.png'
  },
  {
    name: 'Map',
    to: `${MAIN_ROUTE}map`,
    icon: '/map.png'
  },
  {
    name: 'Dashboard',
    to: '/dashboard',
    icon: '/chat.png'
  },
  {
    name: 'Agentes',
    to: `${MAIN_ROUTE}agentes`,
    icon: '/cocoCapi.png'
  },
];
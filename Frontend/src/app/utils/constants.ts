const MAIN_ROUTE = '/pages/';

export type NavigationRoute = {
  name: string;
  to: string;
  icon: string;
  clientVisible?: boolean;
};

export const ROUTES: NavigationRoute[] = [
  {
    name: 'Home2',
    to: `${MAIN_ROUTE}home`,
    icon: '/home.png',
    clientVisible: false,
  },
  {
    name: 'Home',
    to: `${MAIN_ROUTE}home2`,
    icon: '/home.png',
    clientVisible: true,
  },
  {
    name: 'Map',
    to: `${MAIN_ROUTE}map`,
    icon: '/map.png',
    clientVisible: true,
  },
  {
    name: 'Dashboard2',
    to: '/dashboard',
    icon: '/chat.png',
    clientVisible: false,
  },
  {
    name: 'Dashboard',
    to: '/dashboard2',
    icon: '/chat.png',
    clientVisible: true,
  },
  {
    name: 'Agentes',
    to: `${MAIN_ROUTE}agentes`,
    icon: '/cocoCapi.png',
    clientVisible: false,
  },
];
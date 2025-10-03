/**
 * Ruta: Frontend/src/app/components/HUD/HUDNavigator.tsx
 * Descripción: Navigator flotante con estética del chat HUD para navegación global
 * Estado: Activo
 * Autor: Claude Code (actualizado por Codex)
 * Referencias: GlobalChatOverlay.module.css, ROUTES constants
 */

'use client';

import React, { useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ROUTES } from '@/app/utils/constants';
import styles from './HUDNavigator.module.css';

const isRouteActive = (currentPath: string, target: string): boolean => {
  if (currentPath === target) {
    return true;
  }

  if (target === '/') {
    return currentPath === '/';
  }

  return currentPath.startsWith(`${target}/`);
};

export default function HUDNavigator() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    ROUTES.forEach((route) => {
      if (route.to !== pathname) {
        try {
          router.prefetch(route.to);
        } catch (error) {
          /* ignore optional prefetch errors */
        }
      }
    });
  }, [pathname, router]);

  if (!pathname) {
    return null;
  }

  return (
    <nav className={styles.navigatorShell} aria-label="Global navigation">
      <ul className={styles.navigatorList}>
        {ROUTES.map((route) => {
          const active = isRouteActive(pathname, route.to);

          return (
            <li key={route.to} className={styles.navigatorItem}>
              <Link
                href={route.to}
                prefetch
                className={`${styles.navigatorButton} ${active ? styles.navigatorButtonActive : ''}`}
                aria-label={route.name}
                aria-current={active ? 'page' : undefined}
              >
                <span className={styles.navigatorIcon}>
                  <Image src={route.icon} alt="" width={18} height={18} aria-hidden />
                </span>
                <span className={styles.navigatorLabel}>{route.name}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

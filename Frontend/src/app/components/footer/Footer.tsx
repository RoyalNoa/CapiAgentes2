'use client';

import "./styles.css";
import HUDSwitch from "../HUD/HUDSwitch";
import { useNavigationMode } from "@/app/contexts/NavigationModeContext";

export default function Footer() {
    const { isDeveloper, setMode } = useNavigationMode();

    const handleToggle = (checked: boolean) => {
        setMode(checked ? 'developer' : 'client');
    };

    return (
        <footer className="FooterStyle">
            <div className="footerContent">
                <div className="iconCapi" />
                <h2 className="textIcon">IA proyect</h2>
            </div>

            <div className="footerToggle" aria-live="polite">
                <span className="footerToggleLabel">Modo navegación</span>
                <HUDSwitch
                    checked={isDeveloper}
                    onChange={handleToggle}
                    label={isDeveloper ? 'Dev' : 'Client'}
                    id="navigation-mode-toggle"
                    className="footerToggleSwitch"
                />
                <span className="footerToggleStatus">
                    {isDeveloper ? 'Mostrar todas las vistas' : 'Vista básica'}
                </span>
            </div>
        </footer>
    );
}
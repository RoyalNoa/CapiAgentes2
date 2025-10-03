"use client"

import dynamic from "next/dynamic"
import { useCallback, useEffect, useState } from "react"
import "../../components/loader/styles.css"
import { useGlobalChatIntegration } from "../../hooks/useGlobalChatIntegration"
import Loader from "../../components/loader/Loader"
import styles from "./mapPage.module.css"

const GoogleMap = dynamic(() => import("./google/GoogleMapView"), { ssr: false })

interface ModernBranch {
  sucursal_id: string
  sucursal_numero: number
  sucursal_nombre: string
  telefonos?: string | null
  calle?: string | null
  altura?: number | null
  barrio?: string | null
  comuna?: number | null
  codigo_postal?: number | null
  codigo_postal_argentino?: string | null
  saldo_total_sucursal: number
  caja_teorica_sucursal?: number | null
  total_atm: number
  total_ats: number
  total_tesoro: number
  total_cajas_ventanilla: number
  total_buzon_depositos: number
  total_recaudacion: number
  total_caja_chica: number
  total_otros: number
  direccion_sucursal?: string | null
  latitud: number
  longitud: number
  observacion?: string | null
}

export default function Mapa() {
  const [loader, setLoader] = useState(true)
  const [googleSelection, setGoogleSelection] = useState<ModernBranch | null>(null)
  const [simulationTrigger, setSimulationTrigger] = useState(0)
  const [isSimulationRunning, setIsSimulationRunning] = useState(false)
  const [isGoogleMapReady, setIsGoogleMapReady] = useState(false)

  const {
    selectedSucursal,
    setSelectedSucursal,
    sendMessageAndOpen,
  } = useGlobalChatIntegration()

  useEffect(() => {
    if (typeof document === "undefined") {
      return
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  useEffect(() => {
    const id = setTimeout(() => setLoader(false), 3000)
    return () => clearTimeout(id)
  }, [])

  const handleSucursalSelect = useCallback((sucursal: ModernBranch | null) => {
    if (!sucursal) {
      setGoogleSelection(null)
      setSelectedSucursal(null)
      return
    }

    setGoogleSelection(sucursal)
    setSelectedSucursal(sucursal)
  }, [setSelectedSucursal])

  const handleSimulationClick = useCallback(() => {
    if (isSimulationRunning || !isGoogleMapReady) {
      return
    }
    setSimulationTrigger((prev) => prev + 1)
  }, [isGoogleMapReady, isSimulationRunning])

  if (loader) {
    return <Loader />
  }

  return (
    <>
      <div className={styles.googleContainer}>
        <div className={styles.simulationControls}>
          <button
            className={styles.simulationButton}
            onClick={handleSimulationClick}
            disabled={isSimulationRunning || !isGoogleMapReady}
          >
            {isSimulationRunning
              ? "Simulando..."
              : isGoogleMapReady
                ? "Iniciar simulacion"
                : "Preparando mapa..."}
          </button>
        </div>

        <div className={styles.googleShell}>
          <GoogleMap
            onSucursalSelect={handleSucursalSelect}
            selectedSucursal={googleSelection}
            simulationTrigger={simulationTrigger}
            onSimulationStateChange={setIsSimulationRunning}
            onReadyStateChange={setIsGoogleMapReady}
          />

          {selectedSucursal && (
            <div className={styles.infoOverlay}>
              <h3 className={styles.infoOverlayTitle}>Sucursal seleccionada</h3>
              <div className={styles.infoRow}>Nombre: {selectedSucursal.sucursal_nombre}</div>
              <div className={styles.infoRow}>Direccion: {selectedSucursal.calle} {selectedSucursal.altura}</div>
              <div className={styles.infoRow}>Barrio: {selectedSucursal.barrio}</div>
              <div className={styles.infoRow}>Telefonos: {selectedSucursal.telefonos}</div>
              <div className={styles.infoRow}>Comuna: {selectedSucursal.comuna} / CP: {selectedSucursal.codigo_postal}</div>
              <div className={styles.infoActions}>
                <button
                  className={styles.infoActionPrimary}
                  onClick={() => sendMessageAndOpen(
                    `Analizar datos de la sucursal ${selectedSucursal.sucursal_nombre}`,
                    { sucursal: selectedSucursal }
                  )}
                >
                  Analizar con IA
                </button>
                <button
                  className={styles.infoActionSecondary}
                  onClick={() => setSelectedSucursal(null)}
                >
                  Limpiar
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

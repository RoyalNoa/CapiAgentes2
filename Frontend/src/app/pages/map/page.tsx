"use client"

import dynamic from "next/dynamic"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { PointerEvent as ReactPointerEvent } from "react"
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

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)
const BALANCE_TOLERANCE = 0.4

export default function Mapa() {
  const [loader, setLoader] = useState(true)
  const [googleSelection, setGoogleSelection] = useState<ModernBranch | null>(null)
  const [simulationTrigger, setSimulationTrigger] = useState(0)
  const [isSimulationRunning, setIsSimulationRunning] = useState(false)
  const [isGoogleMapReady, setIsGoogleMapReady] = useState(false)
  const [overlayPosition, setOverlayPosition] = useState<{ left: number; top: number } | null>(null)
  const [isDraggingOverlay, setIsDraggingOverlay] = useState(false)
  const googleShellRef = useRef<HTMLDivElement | null>(null)
  const overlayRef = useRef<HTMLDivElement | null>(null)
  const dragOffsetRef = useRef<{ x: number; y: number } | null>(null)

  const {
    selectedSucursal,
    setSelectedSucursal,
    sendMessageAndOpen,
  } = useGlobalChatIntegration()

  const currencyFormatter = useMemo(() => new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 2,
  }), [])

  const formatCurrencyValue = useCallback((value: unknown) => {
    if (value === null || value === undefined) {
      return "N/D"
    }
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) {
      return "N/D"
    }
    return currencyFormatter.format(numeric)
  }, [currencyFormatter])

  const balanceInfo = useMemo(() => {
    const rawCaja = selectedSucursal?.caja_teorica_sucursal
    const rawSaldo = selectedSucursal?.saldo_total_sucursal
    const caja = rawCaja !== null && rawCaja !== undefined ? Number(rawCaja) : null
    const saldo = rawSaldo !== null && rawSaldo !== undefined ? Number(rawSaldo) : null

    const cajaValid = caja !== null && Number.isFinite(caja)
    const saldoValid = saldo !== null && Number.isFinite(saldo)

    let trend: "above" | "below" | "neutral" = "neutral"

    if (cajaValid && saldoValid && Math.abs(caja as number) > 0) {
      const ratio = ((saldo as number) - (caja as number)) / Math.abs(caja as number)
      if (ratio > BALANCE_TOLERANCE) {
        trend = "above"
      } else if (ratio < -BALANCE_TOLERANCE) {
        trend = "below"
      }
    }

    return {
      caja: cajaValid ? (caja as number) : null,
      saldo: saldoValid ? (saldo as number) : null,
      trend,
      hasData: cajaValid || saldoValid,
    }
  }, [selectedSucursal])

  const saldoHighlightClass = useMemo(() => {
    if (balanceInfo.trend === "above") {
      return styles.infoMetricHigh
    }
    if (balanceInfo.trend === "below") {
      return styles.infoMetricLow
    }
    return ""
  }, [balanceInfo.trend])

  const recenterOverlay = useCallback(() => {
    const shell = googleShellRef.current
    if (!shell) {
      return
    }

    const { width, height } = shell.getBoundingClientRect()
    const overlayWidth = overlayRef.current?.offsetWidth ?? 0
    const overlayHeight = overlayRef.current?.offsetHeight ?? 0
    const margin = 12
    const verticalOffset = 100
    const minLeft = margin + overlayWidth / 2
    const maxLeft = Math.max(minLeft, width - margin - overlayWidth / 2)
    const minTop = margin + overlayHeight / 2
    const maxTop = Math.max(minTop, height - margin - overlayHeight / 2)

    const proposedLeft = width / 2
    const proposedTop = height / 2 - verticalOffset

    setOverlayPosition({
      left: clamp(proposedLeft, minLeft, maxLeft),
      top: clamp(proposedTop, minTop, maxTop),
    })
  }, [])

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
      setOverlayPosition(null)
      setIsDraggingOverlay(false)
      return
    }

    setGoogleSelection(sucursal)
    setSelectedSucursal(sucursal)
    setIsDraggingOverlay(false)
    recenterOverlay()
  }, [recenterOverlay, setGoogleSelection, setSelectedSucursal])

  const handleClearSelection = useCallback(() => {
    setGoogleSelection(null)
    setSelectedSucursal(null)
    setOverlayPosition(null)
    setIsDraggingOverlay(false)
  }, [setGoogleSelection, setOverlayPosition, setSelectedSucursal])

  const handleOverlayPointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!googleShellRef.current) {
      return
    }

    const target = event.target as HTMLElement | null
    if (target?.closest('button, a, input, textarea, select, label')) {
      return
    }

    const shellRect = googleShellRef.current.getBoundingClientRect()
    const pointerX = event.clientX - shellRect.left
    const pointerY = event.clientY - shellRect.top
    const currentPosition = overlayPosition ?? { left: shellRect.width / 2, top: shellRect.height / 2 }

    dragOffsetRef.current = {
      x: pointerX - currentPosition.left,
      y: pointerY - currentPosition.top,
    }

    setIsDraggingOverlay(true)
    event.currentTarget.setPointerCapture(event.pointerId)
  }, [overlayPosition])

  const handleOverlayPointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!isDraggingOverlay || !dragOffsetRef.current || !googleShellRef.current) {
      return
    }

    const shellRect = googleShellRef.current.getBoundingClientRect()
    const pointerX = event.clientX - shellRect.left
    const pointerY = event.clientY - shellRect.top
    const overlayWidth = overlayRef.current?.offsetWidth ?? 0
    const overlayHeight = overlayRef.current?.offsetHeight ?? 0
    const margin = 12
    const minLeft = margin + overlayWidth / 2
    const maxLeft = Math.max(minLeft, shellRect.width - margin - overlayWidth / 2)
    const minTop = margin + overlayHeight / 2
    const maxTop = Math.max(minTop, shellRect.height - margin - overlayHeight / 2)

    const proposedLeft = pointerX - dragOffsetRef.current.x
    const proposedTop = pointerY - dragOffsetRef.current.y

    setOverlayPosition({
      left: clamp(proposedLeft, minLeft, maxLeft),
      top: clamp(proposedTop, minTop, maxTop),
    })
  }, [isDraggingOverlay])

  const handleOverlayPointerUp = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!isDraggingOverlay) {
      return
    }

    setIsDraggingOverlay(false)
    dragOffsetRef.current = null

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }, [isDraggingOverlay])

  const handleSimulationClick = useCallback(() => {
    if (isSimulationRunning || !isGoogleMapReady) {
      return
    }
    setSimulationTrigger((prev) => prev + 1)
  }, [isGoogleMapReady, isSimulationRunning])

  useEffect(() => {
    if (selectedSucursal && !overlayPosition) {
      recenterOverlay()
    }
  }, [overlayPosition, recenterOverlay, selectedSucursal])

  if (loader) {
    return <Loader />
  }

  return (
    <>
      <div className={styles.googleContainer}>
        <video className={styles.backgroundVideo} autoPlay muted loop playsInline>
          <source src="/videoplayback (1).webm" type="video/webm" />
          Tu navegador no soporta video HTML5.
        </video>
        <div className={styles.backgroundScrim} aria-hidden="true" />

        <div className={styles.contentLayer}>
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

          <div className={styles.googleShell} ref={googleShellRef}>
            <GoogleMap
              onSucursalSelect={handleSucursalSelect}
              selectedSucursal={googleSelection}
              simulationTrigger={simulationTrigger}
              onSimulationStateChange={setIsSimulationRunning}
              onReadyStateChange={setIsGoogleMapReady}
            />

            {selectedSucursal && overlayPosition && (
              <div
                ref={overlayRef}
                className={`${styles.infoOverlay} ${styles.infoOverlayFloating} ${isDraggingOverlay ? styles.infoOverlayDragging : styles.infoOverlayDraggable}`}
                style={{ left: `${overlayPosition.left}px`, top: `${overlayPosition.top}px` }}
                onPointerDown={handleOverlayPointerDown}
                onPointerMove={handleOverlayPointerMove}
                onPointerUp={handleOverlayPointerUp}
                onPointerCancel={handleOverlayPointerUp}
              >
                <h3 className={styles.infoOverlayTitle}>
                  {selectedSucursal.sucursal_nombre ?? "Sucursal"}
                </h3>
                <div className={styles.infoRow}>Direccion: {selectedSucursal.calle} {selectedSucursal.altura}</div>
                <div className={styles.infoRow}>Barrio: {selectedSucursal.barrio}</div>
                <div className={styles.infoRow}>Telefonos: {selectedSucursal.telefonos}</div>
                <div className={styles.infoRow}>Comuna: {selectedSucursal.comuna} / CP: {selectedSucursal.codigo_postal}</div>
                {balanceInfo.hasData && (
                  <div className={styles.infoMetrics}>
                    <div className={styles.infoMetric}>
                      <span className={styles.infoMetricLabel}>Caja teórica</span>
                      <span className={styles.infoMetricValue}>{formatCurrencyValue(balanceInfo.caja)}</span>
                    </div>
                    <div className={styles.infoMetric}>
                      <span className={styles.infoMetricLabel}>Saldo actual</span>
                      <span className={`${styles.infoMetricValue}${saldoHighlightClass ? ` ${saldoHighlightClass}` : ""}`}>
                        {formatCurrencyValue(balanceInfo.saldo)}
                      </span>
                    </div>
                  </div>
                )}
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
                    onClick={handleClearSelection}
                  >
                    Limpiar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

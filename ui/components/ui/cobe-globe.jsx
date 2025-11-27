"use client";
import { useCallback, useEffect, useRef, useState } from "react"
import createGlobe from "cobe"
import { useSpring } from "react-spring"

import { cn } from "@/lib/cn"

export function Cobe({
  variant = "default",
  className,
  style,

  locations = [
    { name: "San Francisco", emoji: "📍" },
    { name: "Berlin", emoji: "📍" },
    { name: "Tokyo", emoji: "📍" },
    { name: "Buenos Aires", emoji: "📍" },
  ],

  // Default values based on the original JSX version
  phi = 0,

  theta = 0.2,
  mapSamples = 16000,
  mapBrightness = 1.8,
  mapBaseBrightness = 0.05,
  diffuse = 3,
  dark = 1.0,
  baseColor = "#ffffff",
  markerColor = "#fb6415",
  markerSize = 0.05,
  glowColor = "#ffffff",
  scale = 1.0,
  offsetX = 0.0,
  offsetY = 0.0,
  opacity = 0.7
}) {
  const canvasRef = useRef(null)
  const pointerInteracting = useRef(null)
  const pointerInteractionMovement = useRef(0)
  const focusRef = useRef([0, 0])
  const [customLocations, setCustomLocations] = useState([])
  const [isInitializing, setIsInitializing] = useState(true)

  const [{ r }, api] = useSpring(() => ({
    r: 0,
    config: {
      mass: 1,
      tension: 280,
      friction: 40,
      precision: 0.001,
    },
  }))

  const locationToAngles = (lat, long) => {
    return [Math.PI - ((long * Math.PI) / 180 - Math.PI / 2), (lat * Math.PI) / 180];
  }

  const hexToRgb = hex => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result
      ? [
          parseInt(result[1], 16) / 255,
          parseInt(result[2], 16) / 255,
          parseInt(result[3], 16) / 255,
        ]
      : [0, 0, 0];
  }

  const geocodeLocation = async query => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`
      )
      const data = await response.json()

      if (data && data.length > 0) {
        return {
          lat: parseFloat(data[0].lat),
          lng: parseFloat(data[0].lon),
          display_name: data[0].display_name,
        };
      }
      return null
    } catch (error) {
      console.error("Geocoding error:", error)
      return null
    }
  }

  const geocodeLocationList = useCallback(async (locationList) => {
    const geocodedLocations = []

    for (const location of locationList) {
      if (location.lat && location.long) {
        // Already has coordinates
        geocodedLocations.push(location)
      } else {
        // Need to geocode
        const result = await geocodeLocation(location.name)
        if (result) {
          geocodedLocations.push({
            ...location,
            lat: result.lat,
            long: result.lng,
          })
        }
      }
    }

    return geocodedLocations
  }, [])

  // Initialize locations on component mount
  useEffect(() => {
    const initializeLocations = async () => {
      if (variant === "rotate-to-location" && locations.length > 0) {
        setIsInitializing(true)
        const geocoded = await geocodeLocationList(locations)
        setCustomLocations(geocoded)
        setIsInitializing(false)
      }
    }

    initializeLocations()
  }, [variant, locations, geocodeLocationList])

  useEffect(() => {
    let phi = 0
    let width = 0
    let currentPhi = 0
    let currentTheta = 0
    const doublePi = Math.PI * 2

    const onResize = () => {
      if (canvasRef.current) {
        width = canvasRef.current.offsetWidth
      }
    }

    window.addEventListener("resize", onResize)
    onResize()

    if (!canvasRef.current) return

    const globe = createGlobe(canvasRef.current, {
      devicePixelRatio: 2,
      width: width * 2,
      height: variant === "scaled" ? width * 2 * 0.4 : width * 2,
      phi: phi,
      theta: theta,
      dark: dark,
      diffuse: diffuse,
      mapSamples: mapSamples,
      mapBrightness: mapBrightness,
      mapBaseBrightness: mapBaseBrightness,
      baseColor: hexToRgb(baseColor),
      markerColor: hexToRgb(markerColor),
      glowColor: hexToRgb(glowColor),
      markers:
        variant === "default" ||
        variant === "draggable" ||
        variant === "auto-draggable" ||
        variant === "auto-rotation" ||
        variant === "scaled"
          ? [
              // San Francisco, default color
              { location: [37.7595, -122.4367], size: markerSize },
              // New York, red color
              {
                location: [40.7128, -74.006],
                size: markerSize,
                color: [1, 0, 0],
              },
              // Tokyo, blue color
              {
                location: [35.6895, 139.6917],
                size: markerSize,
                color: [0, 0.5, 1],
              },
              // Sydney, green color
              {
                location: [-33.8688, 151.2093],
                size: markerSize,
                color: [0, 1, 0],
              },
              // Rio de Janeiro, purple color
              {
                location: [-22.9068, -43.1729],
                size: markerSize,
                color: [0.8, 0, 0.8],
              },
              // Paris, yellow color
              {
                location: [48.8566, 2.3522],
                size: markerSize,
                color: [1, 1, 0],
              },
              // Porto, orange color
              {
                location: [41.1579, -8.6291],
                size: markerSize,
                color: [1, 0.5, 0],
              },
              // Athens, pink color
              {
                location: [37.9838, 23.7275],
                size: markerSize,
                color: [1, 0.5, 1],
              },
              // Rome, brown color
              {
                location: [41.9028, 12.4964],
                size: markerSize,
                color: [0.5, 0.3, 0],
              },
              // Kathmandu, blue color
              {
                location: [27.7172, 85.324],
                size: markerSize,
                color: [0, 0.5, 1],
              },
              // Tarbes, green color
              {
                location: [43.4643, -0.5167],
                size: markerSize,
                color: [0, 1, 0],
              },
              // Bamako, yellow color
              {
                location: [12.6683, -8.0076],
                size: markerSize,
                color: [1, 1, 0],
              },
              // Djibouti, purple color
              {
                location: [11.55, 43.1667],
                size: markerSize,
                color: [0.8, 0, 0.8],
              },
            ]
          : variant === "rotate-to-location"
            ? customLocations
                .filter((loc) => loc.lat && loc.long)
                .map((loc) => ({
                  location: [loc.lat, loc.long],
                  size: markerSize,
                }))
            : [],
      scale: variant === "scaled" ? 2.5 : undefined,
      offset: variant === "scaled" ? [0, width * 2 * 0.4 * 0.6] : undefined,
      opacity: opacity,
      onRender: (state) => {
        switch (variant) {
          case "default":
            state.phi = phi + r.get()
            phi += 0.005
            break
          case "draggable":
            state.phi = r.get()
            break
          case "auto-draggable":
            if (!pointerInteracting.current) {
              phi += 0.005
            }
            state.phi = phi + r.get()
            break
          case "auto-rotation":
            state.phi = phi
            phi += 0.005
            break
          case "rotate-to-location":
            state.phi = currentPhi
            state.theta = currentTheta
            const [focusPhi, focusTheta] = focusRef.current
            const distPositive = (focusPhi - currentPhi + doublePi) % doublePi
            const distNegative = (currentPhi - focusPhi + doublePi) % doublePi
            if (distPositive < distNegative) {
              currentPhi += distPositive * 0.08
            } else {
              currentPhi -= distNegative * 0.08
            }
            currentTheta = currentTheta * 0.92 + focusTheta * 0.08
            break
          case "scaled":
            // No rotation for scaled variant
            break
        }

        state.width = width * 2
        state.height = variant === "scaled" ? width * 2 * 0.4 : width * 2
      },
    })

    if (canvasRef.current) {
      setTimeout(() => {
        if (canvasRef.current) {
          canvasRef.current.style.opacity = opacity.toString()
        }
      })
    }

    return () => {
      globe.destroy()
      window.removeEventListener("resize", onResize)
    };
  }, [
    variant,
    r,
    customLocations,
    phi,
    theta,
    mapSamples,
    mapBrightness,
    mapBaseBrightness,
    diffuse,
    dark,
    baseColor,
    markerColor,
    markerSize,
    glowColor,
    scale,
    offsetX,
    offsetY,
    opacity,
  ])

  const handlePointerDown = (e) => {
    if (
      variant === "draggable" ||
      variant === "auto-draggable" ||
      variant === "default"
    ) {
      pointerInteracting.current =
        e.clientX - pointerInteractionMovement.current
      if (canvasRef.current) canvasRef.current.style.cursor = "grabbing"
    }
  }

  const handlePointerUp = () => {
    if (
      variant === "draggable" ||
      variant === "auto-draggable" ||
      variant === "default"
    ) {
      pointerInteracting.current = null
      if (canvasRef.current) canvasRef.current.style.cursor = "grab"
    }
  }

  const handlePointerOut = () => {
    if (
      variant === "draggable" ||
      variant === "auto-draggable" ||
      variant === "default"
    ) {
      pointerInteracting.current = null
      if (canvasRef.current) canvasRef.current.style.cursor = "grab"
    }
  }

  const handleMouseMove = (e) => {
    if (
      (variant === "draggable" ||
        variant === "auto-draggable" ||
        variant === "default") &&
      pointerInteracting.current !== null
    ) {
      const delta = e.clientX - pointerInteracting.current
      pointerInteractionMovement.current = delta
      api.start({
        r: delta / 200,
      })
    }
  }

  const handleTouchMove = (e) => {
    if (
      (variant === "draggable" ||
        variant === "auto-draggable" ||
        variant === "default") &&
      pointerInteracting.current !== null &&
      e.touches[0]
    ) {
      const delta = e.touches[0].clientX - pointerInteracting.current
      pointerInteractionMovement.current = delta
      api.start({
        r: delta / 100,
      })
    }
  }

  const handleLocationClick = (lat, long) => {
    if (variant === "rotate-to-location") {
      focusRef.current = locationToAngles(lat, long)
    }
  }

  const containerStyle = {
    width: "100%",
    maxWidth: variant === "scaled" ? 800 : 600,
    aspectRatio: variant === "scaled" ? 2.5 : 1,
    margin: "auto",
    position: "relative",
    ...style,
  }

  const canvasStyle = {
    width: "100%",
    height: "100%",
    contain: "layout paint size",
    opacity: 0,
    transition: "opacity 1s ease",
    cursor:
      variant === "draggable" ||
      variant === "auto-draggable" ||
      variant === "default"
        ? "grab"
        : undefined,
    borderRadius:
      variant === "default" ||
      variant === "draggable" ||
      variant === "auto-draggable" ||
      variant === "auto-rotation"
        ? "50%"
        : variant === "scaled"
          ? "8px"
          : undefined,
  }

  return (
    <div className={cn("", className)} style={containerStyle}>
      <canvas
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerOut={handlePointerOut}
        onMouseMove={handleMouseMove}
        onTouchMove={handleTouchMove}
        style={canvasStyle} />
      {variant === "rotate-to-location" && (
        <>
          <div
            className="control-buttons flex flex-col items-center justify-center md:flex-row"
            style={{ gap: ".5rem" }}>
            {isInitializing ? "Loading locations..." : ""}
            {customLocations
              .filter((loc) => loc.lat && loc.long)
              .map((location, index) => (
                <button
                  key={index}
                  onClick={() =>
                    handleLocationClick(location.lat, location.long)
                  }
                  className="px-4 py-2 bg-white/80 text-black border border-gray-200 rounded-md hover:bg-white/90 transition-all duration-200 hover:scale-105">
                  {location.emoji || "📍"} {location.name}
                </button>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      <div
        data-testid="map-container"
        aria-label="Mars map"
        className="absolute inset-0"
      />
      <aside
        data-testid="route-panel"
        aria-label="Route panel"
        className="absolute left-4 top-4 w-[360px] max-w-[calc(100vw-2rem)] rounded-2xl bg-slate-900/90 p-4 shadow-xl backdrop-blur"
      >
        <h1 className="text-lg font-semibold">Mars Route</h1>
        <p className="mt-1 text-sm text-slate-400">
          Choose an origin and a mineral target to find a safe route.
        </p>
      </aside>
    </div>
  )
}

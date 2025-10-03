export default function Home2Page() {
  return (
    <main className="relative min-h-screen w-full overflow-hidden">
      {/* Background Video */}
      <video
        className="absolute inset-0 h-full w-full object-cover"
        autoPlay
        muted
        loop
        playsInline
      >
        <source src="/videoplayback (1).webm" type="video/webm" />
        Tu navegador no soporta video HTML5.
      </video>

      {/* Foreground: centered capibara above the video */}
      <div className="relative z-10 flex min-h-screen w-full items-center justify-center">
        <img
          src="/cocoCapi.png"
          alt="Capibara CocoCapi"
          className="w-[640px] h-[640px] object-contain drop-shadow-[0_10px_25px_rgba(0,0,0,0.45)]"
        />
      </div>
    </main>
  );
}

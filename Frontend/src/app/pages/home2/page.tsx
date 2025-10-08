import styles from './styles.module.css';

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
        {/* Circular container with the logo video inside */}
        <div className={styles.heroCircle} aria-label="Logo Capi en video" role="img">
          <video className={styles.heroVideo} autoPlay muted loop playsInline>
            <source src="/logocapi.mp4" type="video/mp4" />
            Tu navegador no soporta video HTML5.
          </video>
        </div>
      </div>
    </main>
  );
}

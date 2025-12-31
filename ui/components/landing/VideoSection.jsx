/**
 * VideoSection - Full-screen video section for landing page
 * Displays an MP4 video that fills the entire viewport height
 * Mobile optimized: reduced height, poster fallback, centered focus
 * Related: app/page.jsx, components/landing/*
 */

export default function VideoSection() {
  return (
    <section className="w-full py-8 md:py-16 lg:py-24 px-4 md:px-8 lg:px-16">
      <div className="relative w-full h-[60vh] md:h-[70vh] lg:h-[80vh] max-w-7xl mx-auto overflow-hidden md:rounded-2xl lg:rounded-3xl">
        {/* Video - poster for mobile loading */}
        <video
          autoPlay
          muted
          loop
          playsInline
          className="absolute inset-0 w-full h-full object-cover object-center"
        >
          <source src="/hero-video.mp4" type="video/mp4" />
        </video>
      </div>
    </section>
  );
}

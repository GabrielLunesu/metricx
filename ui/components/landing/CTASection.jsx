"use client";

export default function CTASection() {
  return (
    <div className="w-full bg-white relative overflow-hidden flex flex-col justify-center items-center gap-2">
      <div className="w-full max-w-[1060px] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Content */}
        <div className="self-stretch px-6 md:px-24 py-12 md:py-16 border-t border-b border-[rgba(55,50,47,0.12)] flex justify-center items-center gap-6 relative z-10">
          {/* Background Pattern */}
          <div className="absolute inset-0 w-full h-full overflow-hidden">
            <div className="w-full h-full relative">
              {Array.from({ length: 300 }).map((_, i) => (
                <div
                  key={i}
                  className="absolute h-4 w-full rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                  style={{
                    top: `${i * 16 - 120}px`,
                    left: "-100%",
                    width: "300%",
                  }}
                ></div>
              ))}
            </div>
          </div>

          <div className="w-full max-w-[586px] px-4 md:px-6 py-5 md:py-8 overflow-hidden rounded-lg flex flex-col justify-start items-center gap-6 relative z-20">
            <div className="self-stretch flex flex-col justify-start items-start gap-3">
              <div className="self-stretch text-center flex justify-center flex-col text-[#49423D] text-2xl md:text-3xl lg:text-4xl font-semibold leading-tight md:leading-[50px] font-sans tracking-tight">
                Ready to understand your marketing?
              </div>
              <div className="self-stretch text-center text-[#605A57] text-sm md:text-base leading-6 md:leading-7 font-sans font-medium">
                Join marketers who are making smarter decisions
                <br className="hidden sm:block" />
                with unified data and AI-powered insights.
              </div>
            </div>
            <div className="w-full max-w-[497px] flex flex-col justify-center items-center gap-12">
              <div className="flex justify-start items-center gap-4">
                <a
                  href="/dashboard"
                  className="h-10 md:h-11 px-8 md:px-12 py-[6px] relative bg-[#37322F] shadow-[0px_0px_0px_2.5px_rgba(255,255,255,0.08)_inset] overflow-hidden rounded-full flex justify-center items-center cursor-pointer hover:bg-[#2A2520] transition-colors"
                >
                  <div className="w-44 h-[41px] absolute left-0 top-0 bg-gradient-to-b from-[rgba(255,255,255,0)] to-[rgba(0,0,0,0.10)] mix-blend-multiply"></div>
                  <div className="flex flex-col justify-center text-white text-sm md:text-[15px] font-medium leading-5 font-sans">
                    Start for free
                  </div>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

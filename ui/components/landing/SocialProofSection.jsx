"use client";

function Badge({ icon, text }) {
  return (
    <div className="px-[14px] py-[6px] bg-white shadow-[0px_0px_0px_4px_rgba(55,50,47,0.05)] overflow-hidden rounded-[90px] flex justify-start items-center gap-[8px] border border-[rgba(2,6,23,0.08)]">
      <div className="w-[14px] h-[14px] relative overflow-hidden flex items-center justify-center">{icon}</div>
      <div className="text-center flex justify-center flex-col text-[#37322F] text-xs font-medium leading-3 font-sans">
        {text}
      </div>
    </div>
  );
}

export default function SocialProofSection() {
  const logos = [
    { name: "Meta", icon: "M" },
    { name: "Google", icon: "G" },
    { name: "Shopify", icon: "S" },
    { name: "Stripe", icon: "S" },
    { name: "HubSpot", icon: "H" },
    { name: "Klaviyo", icon: "K" },
    { name: "TikTok", icon: "T" },
    { name: "Slack", icon: "S" },
  ];

  return (
    <div className="w-full bg-white flex flex-col justify-center items-center">
      <div className="w-full max-w-[1060px] border-b border-[rgba(55,50,47,0.12)] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Header */}
        <div className="self-stretch px-4 sm:px-6 md:px-24 py-8 sm:py-12 md:py-16 border-b border-[rgba(55,50,47,0.12)] flex justify-center items-center gap-6">
          <div className="w-full max-w-[586px] px-4 sm:px-6 py-4 sm:py-5 overflow-hidden rounded-lg flex flex-col justify-start items-center gap-3 sm:gap-4">
            <Badge
              icon={
                <svg width="12" height="10" viewBox="0 0 12 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="1" y="3" width="4" height="6" stroke="#37322F" strokeWidth="1" fill="none" />
                  <rect x="7" y="1" width="4" height="8" stroke="#37322F" strokeWidth="1" fill="none" />
                </svg>
              }
              text="Trusted By"
            />
            <div className="w-full max-w-[472.55px] text-center flex justify-center flex-col text-[#49423D] text-xl sm:text-2xl md:text-3xl lg:text-4xl font-semibold leading-tight md:leading-[50px] font-sans tracking-tight">
              Powering marketing teams everywhere
            </div>
            <div className="self-stretch text-center text-[#605A57] text-sm sm:text-base font-normal leading-6 sm:leading-7 font-sans">
              From startups to enterprises, metricx helps teams make
              <br className="hidden sm:block" />
              smarter marketing decisions with unified data.
            </div>
          </div>
        </div>

        {/* Logo Grid */}
        <div className="self-stretch flex justify-center items-start">
          <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
            <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
              {Array.from({ length: 50 }).map((_, i) => (
                <div
                  key={i}
                  className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                />
              ))}
            </div>
          </div>

          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 gap-0 border-l border-r border-[rgba(55,50,47,0.12)]">
            {logos.map((logo, index) => (
              <div
                key={index}
                className={`
                  h-24 xs:h-28 sm:h-32 md:h-36 lg:h-40 flex justify-center items-center gap-2 sm:gap-3
                  border-b border-[rgba(227,226,225,0.5)]
                  ${index % 2 === 0 ? "border-r-[0.5px]" : ""}
                  sm:border-r-[0.5px]
                  border-[#E3E2E1]
                `}
              >
                <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 relative bg-gray-100 rounded-full flex items-center justify-center">
                  <span className="text-sm sm:text-base md:text-lg font-semibold text-gray-600">{logo.icon}</span>
                </div>
                <div className="text-center flex justify-center flex-col text-[#37322F] text-sm sm:text-base md:text-lg lg:text-xl font-medium leading-tight md:leading-9 font-sans">
                  {logo.name}
                </div>
              </div>
            ))}
          </div>

          <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
            <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
              {Array.from({ length: 50 }).map((_, i) => (
                <div
                  key={i}
                  className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export const metadata = {
  title: 'Terms of Service | metricx',
  description: 'metricx Terms of Service - Terms and conditions for using our platform'
};

export default function TermsOfService() {
  return (
    <div className="bg-white antialiased overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-nav border-b border-neutral-200/40 bg-white/80 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          <a href="/" className="flex items-center">
            <img src="/metricx.png" alt="metricx" className="h-12 w-auto" style={{ maxHeight: '48px' }} />
          </a>
          <div className="flex items-center gap-8">
            <a href="/#features" className="text-sm font-medium text-neutral-600 hover:text-cyan-600 transition-colors">Features</a>
            <a href="/#how-it-works" className="text-sm font-medium text-neutral-600 hover:text-cyan-600 transition-colors">How It Works</a>
            <a href="/#showcase" className="text-sm font-medium text-neutral-600 hover:text-cyan-600 transition-colors">Showcase</a>
            <a href="/#contact" className="text-sm font-medium text-neutral-600 hover:text-cyan-600 transition-colors">Contact</a>
            <a href="/dashboard" className="px-6 py-2.5 rounded-full bg-black text-white text-sm font-medium btn-primary">
              Launch Dashboard
            </a>
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="container mx-auto px-4 py-32 max-w-4xl">
        <h1 className="text-4xl font-bold mb-4">Terms of Service</h1>
        <p className="text-muted-foreground mb-8">
          Last Updated: November 7, 2025
        </p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Agreement to Terms</h2>
            <p className="mb-4">
              These Terms of Service ("Terms") constitute a legally binding agreement between you and metricx ("Company," "we," "us," or "our") concerning your access to and use of the metricx platform and services.
            </p>
            <p className="mb-4">
              By accessing or using our services, you agree to be bound by these Terms and our Privacy Policy. If you do not agree to these Terms, you may not access or use our services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Description of Services</h2>
            <p className="mb-4">
              metricx provides a software-as-a-service (SaaS) platform that enables users to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Connect and aggregate advertising data from multiple platforms (Google Ads, Meta Ads, etc.)</li>
              <li>Visualize advertising campaign performance through dashboards and analytics</li>
              <li>Query advertising data using natural language questions</li>
              <li>Generate insights and reports about advertising performance</li>
              <li>Track financial metrics and return on advertising spend</li>
            </ul>
            <p className="mb-4">
              We reserve the right to modify, suspend, or discontinue any aspect of the services at any time, with or without notice.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. Eligibility and Account Registration</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.1 Eligibility</h3>
            <p className="mb-4">
              You must be at least 18 years old and have the legal capacity to enter into binding contracts. By using our services, you represent and warrant that you meet these requirements.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.2 Account Registration</h3>
            <p className="mb-4">
              To use metricx, you must create an account by providing accurate and complete information. You agree to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Provide accurate, current, and complete registration information</li>
              <li>Maintain and update your information to keep it accurate and complete</li>
              <li>Maintain the security of your account credentials</li>
              <li>Notify us immediately of any unauthorized access to your account</li>
              <li>Accept responsibility for all activities that occur under your account</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.3 Organization Accounts</h3>
            <p className="mb-4">
              If you create an account on behalf of an organization, you represent that you have authority to bind that organization to these Terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. User Responsibilities and Conduct</h2>
            <p className="mb-4">
              You agree to use metricx in compliance with all applicable laws and regulations. You agree NOT to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Use the services for any illegal purpose or in violation of any laws</li>
              <li>Attempt to gain unauthorized access to any part of the services or other users' accounts</li>
              <li>Interfere with or disrupt the integrity or performance of the services</li>
              <li>Reverse engineer, decompile, or disassemble any part of the platform</li>
              <li>Use automated systems (bots, scrapers) to access the services without authorization</li>
              <li>Upload or transmit viruses, malware, or other malicious code</li>
              <li>Violate the terms of service of connected advertising platforms</li>
              <li>Share or resell access to the services without authorization</li>
              <li>Remove, obscure, or alter any proprietary notices</li>
              <li>Use the services to compete with or create a similar product</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Third-Party Platform Integrations</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">5.1 Advertising Platform Connections</h3>
            <p className="mb-4">
              metricx integrates with third-party advertising platforms (Google Ads, Meta Ads, etc.) via OAuth authorization. When you connect these platforms:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>You grant metricx permission to access data from those platforms as specified in OAuth consent screens</li>
              <li>You remain subject to the terms of service and privacy policies of those platforms</li>
              <li>You are responsible for maintaining valid authorization and compliance with platform policies</li>
              <li>We are not responsible for changes to third-party APIs or terms that affect functionality</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">5.2 Data Accuracy</h3>
            <p className="mb-4">
              While we strive for accuracy, metricx relies on data provided by third-party platforms. We do not guarantee that advertising metrics will exactly match platform native interfaces due to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>API limitations and data sampling</li>
              <li>Timezone and currency conversion differences</li>
              <li>Data processing delays</li>
              <li>Attribution model variations</li>
            </ul>
            <p className="mb-4">
              You should use platform native interfaces as the source of truth for billing and official reporting.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">5.3 Revocation of Access</h3>
            <p className="mb-4">
              You may revoke metricx's access to your advertising platforms at any time through:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>The metricx platform (Settings → Connections → Disconnect)</li>
              <li>The respective platform's authorization management interface</li>
            </ul>
            <p className="mb-4">
              Revoking access will prevent metricx from syncing new data but will not delete historical data unless you request deletion.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Intellectual Property Rights</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">6.1 metricx Intellectual Property</h3>
            <p className="mb-4">
              The metricx platform, including all software, designs, text, graphics, and other content, is owned by or licensed to metricx and is protected by intellectual property laws. You are granted a limited, non-exclusive, non-transferable license to use the services in accordance with these Terms.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">6.2 Your Content and Data</h3>
            <p className="mb-4">
              You retain all rights to your advertising data and content. By using metricx, you grant us a limited license to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Access, store, and process your advertising data to provide services</li>
              <li>Use aggregated, anonymized data for service improvement and analytics</li>
              <li>Display your data within the platform for your authorized users</li>
            </ul>
            <p className="mb-4">
              We do not claim ownership of your data and will not use it for purposes other than providing and improving our services.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">6.3 Feedback and Suggestions</h3>
            <p className="mb-4">
              Any feedback, suggestions, or ideas you provide about metricx become our property, and we may use them without restriction or compensation.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Payment and Subscription Terms</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.1 Pricing</h3>
            <p className="mb-4">
              Pricing for metricx services is available on our website. We reserve the right to change pricing with 30 days' notice to existing customers.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.2 Billing</h3>
            <p className="mb-4">
              Subscription fees are billed in advance on a monthly or annual basis. By providing payment information, you authorize us to charge the applicable fees automatically.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.3 Refunds</h3>
            <p className="mb-4">
              Subscription fees are generally non-refundable. Refund requests will be considered on a case-by-case basis at our sole discretion.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.4 Free Trials</h3>
            <p className="mb-4">
              We may offer free trials for new users. At the end of the trial period, you will be charged unless you cancel before the trial ends.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.5 Cancellation</h3>
            <p className="mb-4">
              You may cancel your subscription at any time. Cancellation takes effect at the end of your current billing period. You will retain access to the services until that date.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Data Privacy and Security</h2>
            <p className="mb-4">
              Our collection and use of personal information is governed by our Privacy Policy, which is incorporated into these Terms by reference. By using metricx, you consent to our data practices as described in the Privacy Policy.
            </p>
            <p className="mb-4">
              We implement industry-standard security measures to protect your data, including:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Encryption of sensitive data at rest and in transit</li>
              <li>Secure authentication and access controls</li>
              <li>Regular security audits and updates</li>
              <li>Workspace isolation to prevent cross-customer data access</li>
            </ul>
            <p className="mb-4">
              However, no system is completely secure. You acknowledge that you use the services at your own risk.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Disclaimers and Warranties</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">9.1 "As Is" Services</h3>
            <p className="mb-4">
              THE SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMITTED BY LAW, WE DISCLAIM ALL WARRANTIES, INCLUDING:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Implied warranties of merchantability and fitness for a particular purpose</li>
              <li>Non-infringement of third-party rights</li>
              <li>Accuracy, reliability, or completeness of data</li>
              <li>Uninterrupted or error-free service</li>
              <li>Security of data transmission or storage</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">9.2 Third-Party Services</h3>
            <p className="mb-4">
              We are not responsible for the availability, accuracy, or reliability of third-party advertising platforms. Changes to third-party APIs or services may affect metricx functionality without notice.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">9.3 No Financial or Legal Advice</h3>
            <p className="mb-4">
              metricx provides data visualization and analytics tools. We do not provide financial, investment, legal, or tax advice. Consult qualified professionals for such advice.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Limitation of Liability</h2>
            <p className="mb-4">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>metricx SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES</li>
              <li>THIS INCLUDES DAMAGES FOR LOSS OF PROFITS, REVENUE, DATA, OR USE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES</li>
              <li>OUR TOTAL LIABILITY FOR ALL CLAIMS RELATED TO THE SERVICES SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE 12 MONTHS PRIOR TO THE CLAIM</li>
              <li>SOME JURISDICTIONS DO NOT ALLOW LIMITATION OF LIABILITY, SO THESE LIMITATIONS MAY NOT APPLY TO YOU</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Indemnification</h2>
            <p className="mb-4">
              You agree to indemnify, defend, and hold harmless metricx and its officers, directors, employees, and agents from any claims, liabilities, damages, losses, and expenses (including legal fees) arising from:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Your use or misuse of the services</li>
              <li>Your violation of these Terms</li>
              <li>Your violation of any rights of another party</li>
              <li>Your violation of applicable laws or regulations</li>
              <li>Your advertising data or content</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Term and Termination</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">12.1 Term</h3>
            <p className="mb-4">
              These Terms remain in effect while you use the services or maintain an account.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">12.2 Termination by You</h3>
            <p className="mb-4">
              You may terminate your account at any time by contacting us or using in-app account deletion features.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">12.3 Termination by Us</h3>
            <p className="mb-4">
              We may suspend or terminate your access to the services at any time, with or without cause, including if:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>You violate these Terms</li>
              <li>Your account shows fraudulent or suspicious activity</li>
              <li>We are required to do so by law</li>
              <li>You fail to pay applicable fees</li>
              <li>Continued provision would harm us or other users</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">12.4 Effect of Termination</h3>
            <p className="mb-4">
              Upon termination:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Your right to use the services immediately ceases</li>
              <li>We may delete your account and data after a reasonable period</li>
              <li>You remain liable for any fees incurred before termination</li>
              <li>Provisions that by their nature should survive (liability, indemnification, etc.) will continue</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Dispute Resolution</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">13.1 Informal Resolution</h3>
            <p className="mb-4">
              Before filing any formal claim, you agree to contact us to attempt informal resolution of disputes.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">13.2 Arbitration</h3>
            <p className="mb-4">
              Any disputes that cannot be resolved informally shall be resolved through binding arbitration, rather than in court, except that:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Either party may seek injunctive relief in court for intellectual property disputes</li>
              <li>Small claims court actions are permitted</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">13.3 Class Action Waiver</h3>
            <p className="mb-4">
              You agree to resolve disputes only on an individual basis and waive any right to participate in class actions or class-wide arbitration.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. General Provisions</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.1 Governing Law</h3>
            <p className="mb-4">
              These Terms are governed by and construed in accordance with applicable laws, without regard to conflict of law principles.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.2 Changes to Terms</h3>
            <p className="mb-4">
              We may modify these Terms at any time. When we do:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>We will update the "Last Updated" date</li>
              <li>We will notify you of material changes via email or in-app notification</li>
              <li>Continued use after changes constitutes acceptance</li>
            </ul>
            <p className="mb-4">
              If you do not agree to modified Terms, you must stop using the services.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.3 Assignment</h3>
            <p className="mb-4">
              You may not assign or transfer your rights under these Terms without our written consent. We may assign our rights without restriction.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.4 Severability</h3>
            <p className="mb-4">
              If any provision of these Terms is found to be invalid or unenforceable, the remaining provisions will remain in full force and effect.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.5 Entire Agreement</h3>
            <p className="mb-4">
              These Terms, together with our Privacy Policy, constitute the entire agreement between you and metricx regarding the services.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.6 No Waiver</h3>
            <p className="mb-4">
              Our failure to enforce any provision of these Terms does not constitute a waiver of that provision.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">14.7 Force Majeure</h3>
            <p className="mb-4">
              We are not liable for any failure or delay in performance due to circumstances beyond our reasonable control.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">15. Contact Information</h2>
            <p className="mb-4">
              If you have questions about these Terms, please contact us:
            </p>
            <div className="bg-muted p-4 rounded-lg">
              <p className="mb-2"><strong>metricx</strong></p>
              <p className="mb-2">Website: <a href="https://www.metricx.ai" className="text-primary hover:underline">www.metricx.ai</a></p>
              <p className="mb-2">Legal Inquiries: Available through in-app support</p>
            </div>
          </section>

          <section className="mt-12 pt-8 border-t">
            <p className="text-sm text-muted-foreground">
              By using metricx, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service.
            </p>
            <p className="text-sm text-muted-foreground mt-4">
              Last Updated: November 7, 2025
            </p>
          </section>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-12 px-8 border-t border-neutral-200/60">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between flex-wrap gap-8">
            <a href="/" className="flex items-center">
              <img src="/metricx.png" alt="metricx" className="h-12 w-auto" style={{ maxHeight: '48px' }} />
            </a>
            <nav className="flex items-center gap-8 flex-wrap">
              <a href="/#features" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Features</a>
              <a href="/#how-it-works" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">How It Works</a>
              <a href="/#showcase" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Showcase</a>
              <a href="/#contact" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Contact</a>
            </nav>
          </div>
          <div className="mt-8 pt-8 border-t border-neutral-200/60 flex items-center justify-between flex-wrap gap-4">
            <p className="text-sm text-neutral-500">© 2024 metricx. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <a href="/privacy" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Privacy Policy</a>
              <a href="/terms" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Terms of Service</a>
              <a href="/settings" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Delete My Data</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}


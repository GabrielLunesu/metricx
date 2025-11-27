export const metadata = {
  title: 'Privacy Policy | metricx',
  description: 'metricx Privacy Policy - How we collect, use, and protect your data'
};

export default function PrivacyPolicy() {
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
        <h1 className="text-4xl font-bold mb-4">Privacy Policy</h1>
        <p className="text-muted-foreground mb-8">
          Last Updated: November 7, 2025
        </p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="mb-4">
              metricx ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our advertising analytics platform and services.
            </p>
            <p className="mb-4">
              By using metricx, you agree to the collection and use of information in accordance with this policy. If you do not agree with our policies and practices, please do not use our services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.1 Information You Provide</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Account Information:</strong> Name, email address, and password when you create an account</li>
              <li><strong>Workspace Information:</strong> Company name and workspace settings</li>
              <li><strong>Profile Information:</strong> Any additional information you choose to add to your profile</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.2 Advertising Platform Data</h3>
            <p className="mb-4">
              When you connect your advertising accounts (Google Ads, Meta Ads, etc.), we collect:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Campaign Data:</strong> Campaign names, statuses, objectives, and hierarchy (campaigns, ad sets, ads)</li>
              <li><strong>Performance Metrics:</strong> Impressions, clicks, conversions, spend, revenue, and other metrics provided by advertising platforms</li>
              <li><strong>Account Metadata:</strong> Account IDs, currency settings, timezone information</li>
              <li><strong>Creative Assets:</strong> Ad copy, images, and other creative elements (metadata only, not stored permanently)</li>
              <li><strong>Authentication Tokens:</strong> OAuth access tokens and refresh tokens to maintain connection to your advertising accounts</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.3 Usage Information</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Log Data:</strong> IP address, browser type, pages visited, time and date of visits</li>
              <li><strong>Query Logs:</strong> Natural language questions you ask our analytics system</li>
              <li><strong>Device Information:</strong> Device type, operating system, unique device identifiers</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.4 Cookies and Tracking</h3>
            <p className="mb-4">
              We use cookies and similar tracking technologies to maintain your session, remember preferences, and analyze usage patterns. You can control cookies through your browser settings.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
            <p className="mb-4">We use the collected information for the following purposes:</p>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.1 Core Service Delivery</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Display your advertising campaign performance in unified dashboards</li>
              <li>Generate analytics, insights, and visualizations of your advertising data</li>
              <li>Process natural language queries about your advertising performance</li>
              <li>Synchronize data from connected advertising platforms</li>
              <li>Calculate derived metrics (ROAS, CPA, CTR, etc.) from base data</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.2 Platform Improvement</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Analyze usage patterns to improve user experience</li>
              <li>Develop new features and capabilities</li>
              <li>Train and improve our natural language processing models</li>
              <li>Monitor system performance and troubleshoot issues</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.3 Communication</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Send service-related notifications and updates</li>
              <li>Respond to your inquiries and support requests</li>
              <li>Send important security or policy updates</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">3.4 Security and Compliance</h3>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Detect and prevent fraud or unauthorized access</li>
              <li>Comply with legal obligations and enforce our terms</li>
              <li>Protect the rights and safety of metricx and our users</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. How We Share Your Information</h2>
            <p className="mb-4">
              We do not sell your personal information or advertising data to third parties. We may share your information only in the following circumstances:
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">4.1 With Your Consent</h3>
            <p className="mb-4">
              We will share information when you explicitly authorize us to do so.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">4.2 Service Providers</h3>
            <p className="mb-4">
              We may share information with trusted third-party service providers who assist us in operating our platform:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Cloud Infrastructure:</strong> AWS, Google Cloud, or similar providers for hosting and storage</li>
              <li><strong>Analytics Services:</strong> Tools that help us understand platform usage (aggregated data only)</li>
              <li><strong>AI/ML Services:</strong> OpenAI and similar services for natural language processing (query text only, not raw advertising data)</li>
            </ul>
            <p className="mb-4">
              All service providers are contractually obligated to protect your data and use it only for specified purposes.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">4.3 Legal Requirements</h3>
            <p className="mb-4">
              We may disclose information if required by law, court order, or governmental regulation, or if we believe disclosure is necessary to:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Comply with legal process</li>
              <li>Protect our rights or property</li>
              <li>Prevent fraud or security issues</li>
              <li>Protect the safety of users or the public</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">4.4 Business Transfers</h3>
            <p className="mb-4">
              If metricx is involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction. We will notify you via email and/or prominent notice on our platform of any such change.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Data Security</h2>
            <p className="mb-4">
              We implement industry-standard security measures to protect your information:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Encryption at Rest:</strong> All OAuth tokens and sensitive credentials are encrypted using AES-256 encryption</li>
              <li><strong>Encryption in Transit:</strong> All data transmission uses TLS 1.3 or higher</li>
              <li><strong>Access Controls:</strong> Strict workspace isolation ensures you can only access your own data</li>
              <li><strong>Authentication:</strong> Secure password hashing (bcrypt) and JWT-based session management</li>
              <li><strong>Regular Security Audits:</strong> We regularly review and update our security practices</li>
              <li><strong>Secure Infrastructure:</strong> Production systems hosted on security-certified cloud providers</li>
            </ul>
            <p className="mb-4">
              However, no method of transmission over the Internet or electronic storage is 100% secure. While we strive to use commercially acceptable means to protect your information, we cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Data Retention</h2>
            <p className="mb-4">
              We retain your information for as long as necessary to provide our services and comply with legal obligations:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Account Data:</strong> Retained while your account is active and for up to 90 days after account deletion</li>
              <li><strong>Advertising Metrics:</strong> Retained for the duration of your subscription and for up to 12 months after cancellation for historical reporting</li>
              <li><strong>Authentication Tokens:</strong> Deleted immediately when you disconnect an advertising account</li>
              <li><strong>Query Logs:</strong> Retained for up to 24 months for service improvement purposes</li>
              <li><strong>Legal or Compliance Data:</strong> Retained as required by applicable law</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Your Rights and Choices</h2>
            <p className="mb-4">
              You have the following rights regarding your personal information:
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.1 Access and Portability</h3>
            <p className="mb-4">
              You can access and export your data at any time through your account dashboard.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.2 Correction</h3>
            <p className="mb-4">
              You can update your account information and workspace settings directly in the platform.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.3 Deletion</h3>
            <p className="mb-4">
              You can request deletion of your account and associated data. Note that some information may be retained for legal or legitimate business purposes.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.4 Disconnect Advertising Accounts</h3>
            <p className="mb-4">
              You can disconnect any linked advertising account at any time, which will immediately revoke our access and delete associated authentication tokens.
            </p>

            <h3 className="text-xl font-semibold mb-3 mt-6">7.5 Opt-Out of Communications</h3>
            <p className="mb-4">
              You can opt out of non-essential communications by adjusting your notification preferences or following unsubscribe links in emails.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Third-Party Services</h2>
            <p className="mb-4">
              metricx integrates with third-party advertising platforms (Google Ads, Meta Ads, etc.). When you connect these accounts:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>You are subject to the privacy policies and terms of those platforms</li>
              <li>We only access data you authorize through OAuth consent screens</li>
              <li>We do not control how those platforms collect or use your information</li>
              <li>We recommend reviewing the privacy policies of connected platforms</li>
            </ul>
            <p className="mb-4">
              Links to third-party privacy policies:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Google Ads: <a href="https://policies.google.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://policies.google.com/privacy</a></li>
              <li>Meta Ads: <a href="https://www.facebook.com/privacy/policy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://www.facebook.com/privacy/policy</a></li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. International Data Transfers</h2>
            <p className="mb-4">
              Your information may be transferred to and processed in countries other than your country of residence. These countries may have different data protection laws. By using metricx, you consent to the transfer of your information to our facilities and service providers globally.
            </p>
            <p className="mb-4">
              We take steps to ensure that your data receives adequate protection wherever it is processed, including through standard contractual clauses and other appropriate safeguards.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Children's Privacy</h2>
            <p className="mb-4">
              metricx is not intended for use by individuals under the age of 18. We do not knowingly collect personal information from children. If we learn that we have collected information from a child under 18, we will delete it immediately.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. California Privacy Rights (CCPA)</h2>
            <p className="mb-4">
              If you are a California resident, you have additional rights under the California Consumer Privacy Act (CCPA):
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Right to Know:</strong> Request disclosure of personal information collected, used, and shared</li>
              <li><strong>Right to Delete:</strong> Request deletion of personal information</li>
              <li><strong>Right to Opt-Out:</strong> We do not sell personal information</li>
              <li><strong>Right to Non-Discrimination:</strong> We will not discriminate against you for exercising your rights</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. European Privacy Rights (GDPR)</h2>
            <p className="mb-4">
              If you are located in the European Economic Area (EEA), you have rights under the General Data Protection Regulation (GDPR):
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li><strong>Right of Access:</strong> Obtain confirmation of whether we process your data</li>
              <li><strong>Right to Rectification:</strong> Request correction of inaccurate data</li>
              <li><strong>Right to Erasure:</strong> Request deletion of your data</li>
              <li><strong>Right to Restriction:</strong> Request restriction of processing</li>
              <li><strong>Right to Data Portability:</strong> Receive your data in a structured format</li>
              <li><strong>Right to Object:</strong> Object to processing of your data</li>
              <li><strong>Right to Withdraw Consent:</strong> Withdraw consent at any time</li>
            </ul>
            <p className="mb-4">
              Our legal basis for processing your data includes: contract performance, consent, legitimate interests, and legal compliance.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Changes to This Privacy Policy</h2>
            <p className="mb-4">
              We may update this Privacy Policy from time to time. When we make changes, we will:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-4">
              <li>Update the "Last Updated" date at the top of this policy</li>
              <li>Notify you via email for material changes</li>
              <li>Display a prominent notice in the platform</li>
            </ul>
            <p className="mb-4">
              Your continued use of metricx after changes constitutes acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Contact Us</h2>
            <p className="mb-4">
              If you have questions about this Privacy Policy or our data practices, you can contact us at:
            </p>
            <div className="bg-muted p-4 rounded-lg">
              <p className="mb-2"><strong>metricx</strong></p>
              <p className="mb-2">Website: <a href="https://www.metricx.ai" className="text-primary hover:underline">www.metricx.ai</a></p>
              <p className="mb-2">Privacy Inquiries: Available through in-app support</p>
            </div>
          </section>

          <section className="mt-12 pt-8 border-t">
            <p className="text-sm text-muted-foreground">
              This Privacy Policy was last updated on November 7, 2025. We encourage you to review this policy periodically for any changes.
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


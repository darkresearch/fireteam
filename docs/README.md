# Fireteam Documentation

Official documentation for [Fireteam](https://github.com/darkresearch/fireteam) - an autonomous multi-agent software development system powered by Claude AI.

## About

This documentation site is built with [Mintlify](https://mintlify.com) and provides comprehensive guides, API references, and examples for using Fireteam to build software autonomously.

## Running Locally

### Prerequisites

- Node.js 18+ (LTS recommended)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Or with yarn
yarn install
```

### Development Server

Start the local development server:

```bash
npm run dev
```

The documentation will be available at `http://localhost:3000`.

### Building

To build the documentation:

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Documentation Structure

```
fireteam-docs/
├── mint.json              # Mintlify configuration
├── package.json           # Dependencies
├── introduction.mdx       # Homepage
├── quickstart.mdx         # Getting started guide
├── core-concepts/         # Architecture & concepts
│   ├── architecture.mdx
│   ├── agents.mdx
│   └── cycles.mdx
├── installation/          # Setup guides
│   ├── installation.mdx
│   ├── environment.mdx
│   └── requirements.mdx
├── configuration/         # Configuration docs
│   ├── config-file.mdx
│   ├── timeouts.mdx
│   └── sudo-setup.mdx
├── cli-tools/            # CLI reference
│   ├── overview.mdx
│   ├── start-agent.mdx
│   ├── fireteam-status.mdx
│   └── stop-agent.mdx
├── performance/          # Test results & benchmarks
│   ├── test-results.mdx
│   └── benchmarks.mdx
├── advanced/             # Advanced topics
│   ├── state-management.mdx
│   └── improvements.mdx
├── troubleshooting/      # Common issues
│   └── troubleshooting.mdx
└── api/                  # API reference
    ├── overview.mdx
    ├── state-manager.mdx
    ├── agents.mdx
    └── configuration.mdx
```

## Deploying to Mintlify

### Option 1: Mintlify Dashboard

1. Sign up at [Mintlify](https://mintlify.com)
2. Connect your GitHub repository
3. Deploy from the dashboard

### Option 2: Mintlify CLI

```bash
# Install Mintlify CLI globally
npm install -g mintlify

# Deploy
mintlify deploy
```

### Environment Setup

If deploying manually, configure these secrets:

- `MINTLIFY_PROJECT_ID` - Your Mintlify project ID
- `GITHUB_TOKEN` - For GitHub integration (optional)

## Contributing

### Adding New Pages

1. Create MDX file in appropriate directory
2. Add to navigation in `mint.json`:

```json
{
  "group": "Your Section",
  "pages": [
    "path/to/your-page"
  ]
}
```

3. Test locally with `npm run dev`
4. Submit pull request

### Content Guidelines

- Use clear, concise language
- Include code examples where relevant
- Add Mintlify components for better UX:
  - `<Tip>`, `<Warning>`, `<Info>` for callouts
  - `<CodeGroup>` for multi-language examples
  - `<Accordion>` for FAQs
  - `<Card>` for feature highlights
- Follow existing page structure and formatting

### MDX Frontmatter

Every page should have frontmatter:

```mdx
---
title: "Page Title"
description: "Brief description for SEO"
---
```

## Mintlify Components

### Callouts

```mdx
<Tip>Helpful tip for users</Tip>
<Warning>Important warning</Warning>
<Info>Additional information</Info>
```

### Code Groups

```mdx
<CodeGroup>

\`\`\`bash Ubuntu
sudo apt install package
\`\`\`

\`\`\`bash macOS
brew install package
\`\`\`

</CodeGroup>
```

### Cards

```mdx
<CardGroup cols={2}>

<Card title="Title" icon="icon-name" href="/link">
  Description
</Card>

</CardGroup>
```

### Accordions

```mdx
<AccordionGroup>

<Accordion title="Question">
Answer content
</Accordion>

</AccordionGroup>
```

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm run dev
```

### Build Errors

```bash
# Clear cache and rebuild
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Broken Links

Mintlify will warn about broken internal links during `npm run dev`. Check console output.

## Links

- **Live Docs:** https://docs.fireteam.dev (when deployed)
- **Fireteam GitHub:** https://github.com/darkresearch/fireteam
- **Mintlify Docs:** https://mintlify.com/docs
- **Report Issues:** https://github.com/darkresearch/fireteam/issues

## Acknowledgments

- Built with [Mintlify](https://mintlify.com)
- Powered by [Claude AI](https://claude.ai)
- Created by the Fireteam team

---

**Need help?** Open an issue on [GitHub](https://github.com/darkresearch/fireteam/issues) or check the [troubleshooting guide](/troubleshooting/troubleshooting).

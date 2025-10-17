# Quick Start Guide - Fireteam Documentation

## For Developers

### Test Locally
```bash
cd /home/claude/fireteam-docs
npm install
npx mintlify dev
```
Visit: http://localhost:3000

### Make Changes
1. Edit any `.mdx` file in the project
2. Changes auto-reload in dev server
3. Verify in browser

### Add New Page
1. Create `new-page.mdx` in appropriate directory
2. Add frontmatter:
   ```yaml
   ---
   title: "Page Title"
   description: "Page description"
   ---
   ```
3. Add to `mint.json` navigation
4. Test in dev server

## For Deployment

### Option 1: Mintlify Cloud (Recommended)
1. Visit https://mintlify.com
2. Sign up / log in
3. Connect GitHub repo: `darkresearch/fireteam`
4. Set docs directory: `/fireteam-docs` (or root if you move files)
5. Deploy automatically

### Option 2: Self-Hosted
```bash
npx mintlify build
# Outputs static site to _site/
# Deploy _site/ to any static host (Vercel, Netlify, etc.)
```

## Project Structure

```
fireteam-docs/
├── mint.json                    # Main config file
├── package.json                 # Dependencies
├── README.md                    # Full documentation
├── introduction.mdx             # Homepage
├── quickstart.mdx              # Getting started
├── core-concepts/
│   ├── architecture.mdx
│   ├── agents.mdx
│   └── cycles.mdx
├── installation/
│   ├── installation.mdx
│   ├── environment.mdx
│   └── requirements.mdx
├── configuration/
│   ├── config-file.mdx
│   ├── timeouts.mdx
│   └── sudo-setup.mdx
├── cli-tools/
│   ├── overview.mdx
│   ├── start-agent.mdx
│   ├── fireteam-status.mdx
│   └── stop-agent.mdx
├── performance/
│   ├── test-results.mdx
│   └── benchmarks.mdx
├── advanced/
│   ├── state-management.mdx
│   └── improvements.mdx
├── troubleshooting/
│   └── troubleshooting.mdx
└── api/
    ├── overview.mdx
    ├── state-manager.mdx
    ├── agents.mdx
    └── configuration.mdx
```

## Key Files

- **mint.json**: Navigation, branding, colors, settings
- **package.json**: Mintlify CLI version
- **.gitignore**: Excludes node_modules, build artifacts

## Common Tasks

### Update Navigation
Edit `mint.json` → `navigation` array

### Change Branding
Edit `mint.json` → `colors`, `name`, `logo`

### Add Components
Use Mintlify components in MDX:
- `<Card>`, `<CardGroup>`
- `<Tip>`, `<Warning>`, `<Info>`
- `<CodeGroup>`, `<Code>`
- `<Accordion>`, `<AccordionGroup>`

See: https://mintlify.com/docs/components

### Fix Broken Links
Run locally and click through navigation to test all links.

## Status

✅ **PRODUCTION READY** - All 24 pages complete and tested  
✅ No MDX parsing errors  
✅ All technical details verified  
✅ Ready to deploy immediately  

## Next Steps

1. ✅ Review DEPLOYMENT_STATUS.md
2. ⏳ (Optional) Add logo/favicon assets
3. ⏳ Deploy to Mintlify
4. ⏳ Share docs URL with team

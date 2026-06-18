/**
 * Throwaway DEV helper — lets you preview the "Custom tier tracker" populated
 * with the seeded proposals WITHOUT running the full heygov-api / a local DB.
 *
 * It serves only the new endpoints:
 *   GET    /super-secret-admin-endpoints/clerkminutes-proposals
 *   GET    /super-secret-admin-endpoints/clerkminutes-proposals/stats
 *   POST   /super-secret-admin-endpoints/clerkminutes-proposals
 *   PUT    /super-secret-admin-endpoints/clerkminutes-proposals/:id
 *   DELETE /super-secret-admin-endpoints/clerkminutes-proposals/:id
 * ...and forwards EVERYTHING else (login, profile, etc.) to production so your
 * session keeps working.
 *
 * Run:   node dev-proposals-proxy.mjs
 * Then in the dashboard browser console:
 *   localStorage.setItem('heygov-api', 'http://localhost:4500/'); location.reload()
 * To go back to normal:
 *   localStorage.removeItem('heygov-api'); location.reload()
 *
 * Data lives in memory only — restart resets it to the original 23 rows.
 */
import { createServer } from 'node:http'

const PORT = 4500
const UPSTREAM = 'https://api.heygov.com'
const BASE = '/super-secret-admin-endpoints/clerkminutes-proposals'

// The 23 proposals imported from ClerkMinutes_Proposals.xlsx (same as the seed migration)
let nextId = 1
const proposals = [
	['Academica', 'completed', 'Atanas', 9919, null, 'ClerkMinutes Proposal for Academica', null, null, null, '2025-04-15'],
	['Town of Mount Pleasant', 'completed', 'Atanas', 12188, null, 'ClerkMinutes Proposal for Town of Mount Pleasant', null, null, null, '2025-04-15'],
	['Dublin, OH', 'completed', 'Atanas', 7156, null, 'ClerkMinutes Proposal for Dublin, OH', null, null, null, '2025-08-22'],
	['City of Wheat Ridge', 'completed', 'Atanas', 6521, null, 'ClerkMinutes Proposal for City of Wheat Ridge', null, null, null, '2026-02-23'],
	['City of Lincolnton', 'completed', 'Atanas', 3888, null, 'ClerkMinutes Proposal for City of Lincolnton', null, null, null, '2026-01-14'],
	['City of Englewood', 'completed', 'Meagan', 3000, null, 'ClerkMinutes Proposal with Service Order for City of Englewood', null, null, null, '2025-01-17'],
	['City of Newport Beach', 'completed', 'Chris', 4000, null, 'ClerkMinutes Proposal with Service Order Newport Beach', null, null, null, '2025-03-06'],
	['Town of Sherborn, MA', 'completed', 'Atanas', 3777, null, 'ClerkMinutes Proposal for Town of Sherborn, MA', null, null, null, '2025-11-05'],
	['St. Louis Park, MN', 'completed', 'Atanas', 6525, null, 'ClerkMinutes Proposal for St. Louis Park, MN extension', null, null, null, '2025-11-05'],
	['City of Rolling Hills Estate', 'expired', 'Chris', 3765, null, 'ClerkMinutes Proposal for City of Rolling Hills Estate', 'https://app.pandadoc.com/a/#/documents/V6TbLXZXvprsfDri9JSf87/?requestAccessDisabled=true', 'yes', null, '2025-04-22'],
	['Town of Windsor', 'expired', 'Atanas', 5988, 2988, 'ClerkMinutes Proposal for Town of Windsor', null, null, null, '2025-07-28'],
	['Shelby Zomermaand, Joe Wirth', 'expired', 'Atanas', 25995, null, 'ClerkMinutes Proposal_Time Saver Off Site', null, 'yes', null, '2025-06-02'],
	['Marion County, FL', 'expired', 'Atanas', 12134, null, 'ClerkMinutes Proposal for Marion County, FL', 'https://app.pandadoc.com/a/#/documents/qw7LJp4irStYzUCrqqLhvC/?requestAccessDisabled=true', 'no', null, '2025-06-02'],
	['Town of Woodstock, VT', 'expired', 'Chris', 7363, 2988, 'ClerkMinutes Proposal for the Town of Woodstock, VT', 'https://app.pandadoc.com/a/#/documents/yjtkR3W6zXJTwuyieqib2E', null, null, '2025-06-09'],
	['King City', 'expired', 'Atanas', 3188, 3588, 'ClerkMinutes Proposal for King City', null, null, null, '2025-05-15'],
	['Milton Keynes, UK', 'expired', 'Atanas', 6815, null, 'ClerkMinutes Proposal for Milton Keynes, UK', null, 'no', null, '2025-05-30'],
	['Spanish Fork City', 'expired', 'Atanas', 7169, null, 'ClerkMinutes Proposal for Spanish Fork City', 'https://app.pandadoc.com/a/#/documents/8fLPAt9R64BjVREutsnfwi', 'yes', 'Tire Kicker', '2025-05-07'],
	['City of Newport News, VA', 'expired', 'Atanas', 6512, 3588, 'ClerkMinutes Proposal for City of Newport News, VA', null, null, null, '2025-10-30'],
	['City of Fitchburg, WI', 'expired', 'Jelena', 7324, null, 'ClerkMinutes Proposal for City of Fitchburg, WI', 'https://app.pandadoc.com/a/#/documents/3h2Lm2bKghdsRgiuhaDPbi/?requestAccessDisabled=true', 'yes', null, '2025-09-09'],
	['City of Albany', 'viewed', 'Atanas', 9912, null, 'ClerkMinutes Proposal for City of Albany', null, 'yes', 'Started normal plan', '2026-02-11'],
	['San Francisco Bay Ferry', 'viewed', 'Atanas', 9588, 1548, 'ClerkMinutes Proposal for San Francisco Bay Ferry', null, null, null, '2026-02-18'],
	['City of Hollywood, FL', 'viewed', 'Atanas', 15762, null, 'ClerkMinutes Proposal for City of Hollywood, FL', null, null, null, '2026-02-27'],
	['Town of Carslisle, MA', 'completed', 'Atanas', 7164, null, 'ClerkMinutes Proposal for Town of Carslisle, MA', null, null, null, '2026-01-15'],
].map(r => ({
	id: nextId++,
	customer: r[0],
	status: r[1],
	signer: r[2],
	value: r[3] != null ? String(r[3].toFixed ? r[3].toFixed(2) : r[3]) : null,
	plan_purchased: null,
	plan_value: r[4] != null ? String(Number(r[4]).toFixed(2)) : null,
	proposal_name: r[5],
	proposal_url: r[6],
	follow_up: r[7],
	notes: r[8],
	date_created: r[9],
	pricing_file: null,
	pricing_file_name: null,
	pricing_file_type: null,
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString(),
}))

// Start EMPTY by default so importing your CSV populates the tracker from scratch.
// Run with SEED=1 to preload the 23 sample rows instead.
if (!process.env.SEED) {
	proposals.length = 0
	nextId = 1
}

// list view omits the heavy pricing_file blob, exposes a flag instead
const toListItem = p => {
	const { pricing_file, ...rest } = p
	return { ...rest, has_pricing: pricing_file != null }
}

const num = v => (v != null ? Number(v) : 0)
const isSignedCustom = p => p.status === 'completed'
const boughtPlan = p => num(p.plan_value) > 0
// Outcome derived from status: Won = signed custom OR bought a plan; Lost = expired (no plan); else Open
const outcomeOf = p => {
	if (isSignedCustom(p) || boughtPlan(p)) return 'won'
	if (p.status === 'expired') return 'lost'
	return 'open'
}

function computeStats() {
	const wonList = proposals.filter(p => outcomeOf(p) === 'won')
	const lostList = proposals.filter(p => outcomeOf(p) === 'lost')
	const openList = proposals.filter(p => outcomeOf(p) === 'open')
	const decided = wonList.length + lostList.length
	const signedCustomList = proposals.filter(isSignedCustom)
	const planWonList = proposals.filter(boughtPlan)
	const byStatus = {}
	const byPlan = {}
	const byFeature = {}
	const bySigner = {}
	for (const p of proposals) {
		const value = num(p.value)
		const planValue = num(p.plan_value)
		const outcome = outcomeOf(p)
		const acv = boughtPlan(p) ? planValue : value
		byStatus[p.status] ||= { count: 0, value: 0 }
		byStatus[p.status].count += 1
		byStatus[p.status].value += value
		if (planValue > 0) {
			const planKey = p.plan_purchased || 'unspecified'
			byPlan[planKey] ||= { count: 0, revenue: 0 }
			byPlan[planKey].count += 1
			byPlan[planKey].revenue += planValue
		}
		for (const feature of p.features || []) {
			byFeature[feature] ||= { count: 0, won: 0, lost: 0, acv: 0 }
			byFeature[feature].count += 1
			if (outcome === 'won') {
				byFeature[feature].won += 1
				byFeature[feature].acv += acv
			} else if (outcome === 'lost') {
				byFeature[feature].lost += 1
			}
		}
		const signer = p.signer || 'Unassigned'
		bySigner[signer] ||= { count: 0, won: 0, revenue: 0, planRevenue: 0, pipeline: 0 }
		bySigner[signer].count += 1
		if (isSignedCustom(p)) {
			bySigner[signer].won += 1
			bySigner[signer].revenue += value
		} else if (outcome === 'open') {
			bySigner[signer].pipeline += value
		}
		if (planValue > 0) bySigner[signer].planRevenue += planValue
	}
	const customRevenue = signedCustomList.reduce((s, p) => s + num(p.value), 0)
	const planRevenue = planWonList.reduce((s, p) => s + num(p.plan_value), 0)
	return {
		total: proposals.length,
		won: wonList.length,
		open: openList.length,
		lost: lostList.length,
		winRate: decided ? wonList.length / decided : 0,
		signedCustom: signedCustomList.length,
		revenue: customRevenue,
		avgWonValue: signedCustomList.length ? customRevenue / signedCustomList.length : 0,
		planWon: planWonList.length,
		planRevenue,
		totalWonRevenue: customRevenue + planRevenue,
		pipelineValue: openList.reduce((s, p) => s + num(p.value), 0),
		byStatus,
		byPlan,
		byFeature,
		bySigner,
	}
}

function cors(res, req) {
	res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*')
	res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
	res.setHeader('Access-Control-Allow-Headers', req.headers['access-control-request-headers'] || '*')
}

function json(res, status, body) {
	res.statusCode = status
	res.setHeader('content-type', 'application/json')
	res.end(JSON.stringify(body))
}

function readBody(req) {
	return new Promise(resolve => {
		const chunks = []
		req.on('data', c => chunks.push(c))
		req.on('end', () => resolve(Buffer.concat(chunks)))
	})
}

const server = createServer(async (req, res) => {
	if (req.url.includes('clerkminutes-proposals')) {
		console.log(`[${req.method}] ${req.url}`)
	}
	cors(res, req)
	if (req.method === 'OPTIONS') {
		res.statusCode = 204
		return res.end()
	}

	const url = new URL(req.url, `http://localhost:${PORT}`)
	const path = url.pathname

	// --- New proposals endpoints, served locally ---
	if (path === `${BASE}/stats` && req.method === 'GET') {
		return json(res, 200, computeStats())
	}

	if (path === BASE) {
		if (req.method === 'GET') {
			let list = [...proposals]
			const status = url.searchParams.get('status')
			const signer = url.searchParams.get('signer')
			const search = url.searchParams.get('search')
			const feature = url.searchParams.get('feature')
			if (status) list = list.filter(p => p.status === status)
			if (signer) list = list.filter(p => p.signer === signer)
			if (search) list = list.filter(p => (p.customer || '').toLowerCase().includes(search.toLowerCase()))
			if (feature) list = list.filter(p => (p.features || []).includes(feature))
			list.sort((a, b) => String(b.date_created).localeCompare(String(a.date_created)) || b.id - a.id)
			return json(res, 200, list.map(toListItem))
		}
		if (req.method === 'POST') {
			const body = JSON.parse((await readBody(req)).toString() || '{}')
			const created = {
				id: nextId++,
				customer: body.customer,
				status: body.status || 'draft',
				signer: body.signer ?? null,
				value: body.value != null ? String(Number(body.value).toFixed(2)) : null,
				plan_purchased: body.plan_purchased ?? null,
				plan_value: body.plan_value != null ? String(Number(body.plan_value).toFixed(2)) : null,
				proposal_name: body.proposal_name ?? null,
				proposal_url: body.proposal_url ?? null,
				follow_up: body.follow_up ?? null,
				notes: body.notes ?? null,
				features: body.features ?? null,
				date_created: body.date_created ?? null,
				pricing_file: body.pricing_file ?? null,
				pricing_file_name: body.pricing_file_name ?? null,
				pricing_file_type: body.pricing_file_type ?? null,
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
			}
			proposals.push(created)
			return json(res, 201, toListItem(created))
		}
	}

	const pricingMatch = path.match(new RegExp(`^${BASE}/(\\d+)/pricing$`))
	if (pricingMatch && req.method === 'GET') {
		const p = proposals.find(x => x.id === Number(pricingMatch[1]))
		if (!p || !p.pricing_file) return json(res, 404, { message: 'Not found' })
		return json(res, 200, {
			id: p.id,
			pricing_file: p.pricing_file,
			pricing_file_name: p.pricing_file_name,
			pricing_file_type: p.pricing_file_type,
		})
	}

	const idMatch = path.match(new RegExp(`^${BASE}/(\\d+)$`))
	if (idMatch) {
		const id = Number(idMatch[1])
		const p = proposals.find(x => x.id === id)
		if (!p) return json(res, 404, { message: 'Not found' })
		if (req.method === 'PUT') {
			const body = JSON.parse((await readBody(req)).toString() || '{}')
			for (const k of ['customer', 'status', 'signer', 'plan_purchased', 'proposal_name', 'proposal_url', 'follow_up', 'notes', 'features', 'date_created', 'pricing_file', 'pricing_file_name', 'pricing_file_type']) {
				if (k in body) p[k] = body[k]
			}
			if ('value' in body) p.value = body.value != null ? String(Number(body.value).toFixed(2)) : null
			if ('plan_value' in body) p.plan_value = body.plan_value != null ? String(Number(body.plan_value).toFixed(2)) : null
			p.updated_at = new Date().toISOString()
			return json(res, 200, toListItem(p))
		}
		if (req.method === 'DELETE') {
			proposals.splice(proposals.indexOf(p), 1)
			res.statusCode = 204
			return res.end()
		}
	}

	// --- Everything else → forward to production so auth/profile keep working ---
	const upstreamUrl = UPSTREAM + req.url
	const headers = {}
	for (const [k, v] of Object.entries(req.headers)) {
		if (['host', 'connection', 'content-length'].includes(k)) continue
		headers[k] = v
	}
	const init = { method: req.method, headers }
	if (!['GET', 'HEAD'].includes(req.method)) {
		const body = await readBody(req)
		if (body.length) init.body = body
	}
	try {
		const upstream = await fetch(upstreamUrl, init)
		res.statusCode = upstream.status
		const ct = upstream.headers.get('content-type')
		if (ct) res.setHeader('content-type', ct)
		const buf = Buffer.from(await upstream.arrayBuffer())
		res.end(buf)
	} catch (err) {
		json(res, 502, { message: 'Proxy error', error: String(err) })
	}
})

server.listen(PORT, () => {
	console.log(`\n  Dev proposals proxy → http://localhost:${PORT}/`)
	console.log(`  Serving ${proposals.length} seeded proposals; forwarding everything else to ${UPSTREAM}\n`)
	console.log(`  In the dashboard browser console, run:`)
	console.log(`    localStorage.setItem('heygov-api', 'http://localhost:${PORT}/'); location.reload()\n`)
})

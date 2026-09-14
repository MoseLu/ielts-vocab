# Catalog-Wide IPA Audit — Final Report

Generated: 2026-06-17T03:56

## Source
- Full audit: `scripts/audit_all_phonetics.py` (3 sources: Wiktionary, Cambridge Dictionary, ipa-dict en_US)
- Source data: `output/all-ipa-audit/all-words-audit.csv` (12,396 rows)

## Methodology
1. Wiktionary API batch fetch (50 titles/call) — primary RP/GA
2. Cambridge Dictionary per-word scrape (0.2s throttling) — UK + US
3. ipa-dict en_US local TSV (125k entries) — US tiebreaker
4. Strict normalize: strip stress, syllable dots, length marks, R-coloring (ɹ→r)
5. Lenient normalize: ALSO strip parenthesized placeholders `(ə)` `(r)` `(t)` `(d)`, tie-bars `t͡ʃ` `d͡ʒ`
6. 2-source consensus: any two of {Wikt RP, Camb UK, ipa-dict} match lenient-normalized

## Results

| Metric | Strict | Lenient |
|---|---|---|
| UK agreement (Wikt RP = Camb UK) | 3,850 (31.1%) | 3,939 (31.8%) |
| US agreement (Wikt GA = Camb US) | 1,300 (10.5%) | 1,458 (11.8%) |
| Any 2-source | 5,621 (45.3%) | 5,730 (46.2%) |

**167 words** promoted from `no` → `yes` by lenient normalize. Most are Wikt uses of `(r)`, `(ə)`, or `t͡ʃ` tie-bar that Camb spells out.

## Recommended Actions (5,730 words with 2-source consensus)

| Category | Count | Description |
|---|---|---|
| **Already aligned** | 1,842 | Current catalog IPA matches 2-source consensus; no action |
| **Recommended override (unsafe)** | **130** | Catalog has `(ə)`, `(r)`, or `ᵊ` placeholders; clean IPA available |
| **Recommended override (disagreement)** | 24 | Current IPA differs from 2-source consensus; review needed |
| No action (minor diff) | 3,723 | Stress/syllable-dot differences; doesn't affect users |
| Phrases (2+ words) | 803 | Requires separate phrase_policy decision |
| **Total 2-source consensus** | **5,730** | Words where 2+ sources agree lenient-normalized |
| Low confidence (no agreement) | ~5,874 | 3 sources disagree (Wikt missing + cross-dialect) |

## High-Priority: 130 Words with Unsafe Catalog Phonetics

These are the catalog-wide equivalent of the earlier 'unsafe_unfixed' bucket from the luo audit.
Apply the recommended override to fix `(r)`, `(ə)`, or `ᵊ` markers.

| Word | Current (unsafe) | Recommended | Sources |
|---|---|---|---|
| `actor` | `/ˈæktə(r)/` | `/ˈæk.təː/` | W=C(US) |
| `adaptation` | `/ˌædæpˈteɪʃ(ə)n/` | `/ˌæd.əpˈteɪ.ʃən/` | W=I |
| `appear` | `/əˈpɪə(r)/` | `/əˈpɪə/` | W=C(US) |
| `bar` | `/bɑː(r)/` | `/bɑː/` | W=C(US)|C=I |
| `bitter` | `/ˈbɪtə(r)/` | `/ˈbɪt.ə/` |  |
| `boiler` | `/ˈbɔɪlə(r)/` | `/ˈbɔɪlə/` | W=C(US) |
| `border` | `/ˈbɔːdə(r)/` | `/ˈbɔː.də/` | W=C(US) |
| `burglar` | `/ˈbɜːɡlə(r)/` | `/ˈbɜːɡlə(ɹ)/` | W=C(UK)|W=C(US) |
| `cancer` | `/ˈkænsə(r)/` | `/ˈkænsə/` | W=C(US) |
| `chamber` | `/ˈtʃeɪmbə(r)/` | `/ˈtʃeɪmbə(ɹ)/` | W=C(UK)|W=C(US) |
| `cigar` | `/sɪˈɡɑː(r)/` | `/sɪˈɡɑː(ɹ)/` | W=C(UK)|W=I|C=I |
| `cleaner` | `/ˈkliːnə(r)/` | `/ˈkliː.nə/` | W=C(US) |
| `computer` | `/kəmˈpjuːtə(r)/` | `/kəmˈpjuːtə/` |  |
| `confusion` | `/kənˈfjuːʒ(ə)n/` | `/kənˈfjuːʒən/` | W=I |
| `consistency` | `/kənˈsɪst(ə)nsi/` | `/kənˈsɪs.tən.si/` | W=I |
| `core` | `/kɔː(r)/` | `/ko(ː)ɹ/` | C=I |
| `corner` | `/ˈkɔːnə(r)/` | `/ˈkɔːnə(ɹ)/` | W=C(UK)|W=C(US) |
| `cover` | `/ˈkʌvə(r)/` | `/ˈkʌvə/` | W=C(US) |
| `creature` | `/ˈkriːtʃə(r)/` | `/ˈkɹiː.tʃə/` | W=C(US) |
| `customer` | `/ˈkʌstəmə(r)/` | `/ˈkʌs.tə.mə/` | W=C(US) |
| `danger` | `/ˈdeɪndʒə(r)/` | `/ˈdeɪn.d͡ʒə/` | W=C(US) |
| `degradation` | `/ˌdeɡrəˈdeɪʃ(ə)n/` | `/ˌdɛɡɹəˈdeɪʃən/` | W=I |
| `descendants` | `/dɪˈsend(ə)nts/` | `/dɪˈsɛndənts/` | W=I |
| `description` | `/dɪˈskrɪpʃ(ə)n/` | `/dɪˈskɹɪpʃən/` | W=I |
| `deter` | `/dɪˈtɜː(r)/` | `/dɪˈtɜː/` | W=C(US) |
| `disappear` | `/ˌdɪsəˈpɪə(r)/` | `/dɪsəˈpɪə/` | W=C(US) |
| `discover` | `/dɪˈskʌvə(r)/` | `/dɪˈskʌvə/` | W=C(US) |
| `disorder` | `/dɪsˈɔːdə(r)/` | `/dɪsˈɔːdə(ɹ)/` | W=C(UK)|W=C(US) |
| `doctor` | `/ˈdɒktə(r)/` | `/ˈdɒktə(ɹ)/` | W=C(UK)|W=C(US) |
| `encounter` | `/ɪnˈkaʊntə(r)/` | `/ɪnˈkaʊntə/` |  |
| `essence` | `/ˈes(ə)ns/` | `/ˈɛsəns/` | W=I |
| `expedition` | `/ˌekspəˈdɪʃ(ə)n/` | `/ɛkspəˈdɪʃən/` | W=I |
| `expressions` | `/ɪkˈspreʃ(ə)nz/` | `/ɪkˈspɹɛʃ.ənz/` | W=I |
| `fever` | `/ˈfiːvə(r)/` | `/ˈfiːvə/` | W=C(US) |
| `fiction` | `/ˈfɪkʃ(ə)n/` | `/ˈfɪkʃən/` | W=I |
| `filter` | `/ˈfɪltə(r)/` | `/ˈfɪltə/` | W=C(US) |
| `finger` | `/ˈfɪŋɡə(r)/` | `/ˈfɪŋɡəː/` | W=C(US) |
| `founder` | `/ˈfaʊndə(r)/` | `/ˈfaʊ̯n.dəː/` |  |
| `freezer` | `/ˈfriːzə(r)/` | `/ˈfriː.zər/` | W=C(US) |
| `fur` | `/fɜː(r)/` | `/fɜː/` | W=C(US) |
| `future` | `/ˈfjuːtʃə(r)/` | `/ˈfjuː.t͡ʃəː/` | W=C(US) |
| `gather` | `/ˈɡæðə(r)/` | `/ˈɡæðə/` | W=C(US) |
| `guitar` | `/ɡɪˈtɑː(r)/` | `/ɡɪˈtɑː/` | W=C(US)|C=I |
| `harbor` | `/ˈhɑːbə(r)/` | `/ˈhɑːbə/` | W=C(US) |
| `heater` | `/ˈhiːtə(r)/` | `/ˈhiːtə/` |  |
| `heaven` | `/ˈhev(ə)n/` | `/ˈhɛvən/` | W=I |
| `heightened` | `/ˈhaɪt(ə)nd/` | `/ˈhaɪtənd/` | W=I |
| `higher` | `/ˈhaɪə(r)/` | `/ˈhaɪ.ə/` | W=C(US) |
| `hire` | `/ˈhaɪə(r)/` | `/ˈhaɪ(.)ə/` | W=C(US) |
| `horror` | `/ˈhɒrə(r)/` | `/ˈhɒɹ.ə/` | W=C(US) |
| `humour` | `/ˈhjuːmə(r)/` | `/ˈhjuː.mə(ɹ)/` | W=C(UK)|W=C(US) |
| `hunger` | `/ˈhʌŋɡə(r)/` | `/ˈhʌŋɡə/` | W=C(US) |
| `ignore` | `/ɪɡˈnɔː(r)/` | `/ɪɡˈnoə/` | C=I |
| `imagination` | `/ɪˌmædʒɪˈneɪʃ(ə)n/` | `/ɪˌmæd͡ʒəˈneɪʃən/` | W=I |
| `incur` | `/ɪnˈkɜː(r)/` | `/ɪnˈkɜː/` | W=C(US) |
| `indoor` | `/ˈɪndɔː(r)/` | `/ˈɪndɔː/` | C=I |
| `infection` | `/ɪnˈfekʃ(ə)n/` | `/ɪnˈfɛkʃən/` | W=I |
| `infestation` | `/ˌɪnfeˈsteɪʃ(ə)n/` | `/ˌɪnfɛsˈteɪ̯ʃən/` |  |
| `infrastructure` | `/ˈɪnfrəstrʌktʃə(r)/` | `/ˈɪnfɹəˌstɹʌkt͡ʃə/` | W=C(US) |
| `interior` | `/ɪnˈtɪəriə(r)/` | `/ɪnˈtɪə.ɹɪ.ə/` | W=C(US) |
| `interviewer` | `/ˈɪntəvjuːə(r)/` | `/ˈɪntəvjuːə/` |  |
| `invasion` | `/ɪnˈveɪʒ(ə)n/` | `/ɪnˈveɪʒən/` | W=I |
| `irrigation` | `/ˌɪrɪˈɡeɪʃ(ə)n/` | `/ˌɪɹəˈɡeɪʃən/` | W=I |
| `jar` | `/dʒɑː(r)/` | `/d͡ʒɑː/` | W=C(US)|C=I |
| `killer` | `/ˈkɪlə(r)/` | `/ˈkɪlə/` | W=C(US) |
| `ladder` | `/ˈlædə(r)/` | `/ˈlad.ə/` | W=C(US) |
| `litter` | `/ˈlɪtə(r)/` | `/ˈlɪt.ər/` |  |
| `liver` | `/ˈlɪvə(r)/` | `/ˈlɪvə/` | W=C(US) |
| `locker` | `/ˈlɒkə(r)/` | `/ˈlɒk.ə(ɹ)/` | W=C(UK)|W=C(US) |
| `magnificent` | `/mæɡˈnɪfɪs(ə)nt/` | `/mæɡˈnɪfəsənt/` | W=I |
| `manner` | `/ˈmænə(r)/` | `/ˈmænə/` | W=C(US) |
| `manufacturer` | `/ˌmænjuˈfæktʃɚ(ɹ)ɚ/` | `/ˌmænjʊˈfæktʃəɹə/` | W=C(US) |
| `mature` | `/məˈtʃʊə(r)/` | `/məˈt͡ʃɔː(ɹ)/` |  |
| `mediator` | `/ˈmiːdieɪtə(r)/` | `/ˈmiː.di.eɪ.tər/` |  |
| `moisture` | `/ˈmɔɪstʃə(r)/` | `/ˈmɔɪs.t͡ʃə/` | W=C(US) |
| `mother` | `/ˈmʌðə(r)/` | `/ˈmʌð.ə/` | W=C(US) |
| `murder` | `/ˈmɜːdə(r)/` | `/ˈmɜːdə(ɹ)/` | W=C(UK)|W=C(US) |
| `neighbour` | `/ˈneɪbə(r)/` | `/ˈneɪbə/` | W=C(US) |
| `nor` | `/nɔː(r)/` | `/nɔː/` | C=I |
| `obscure` | `/əbˈskjʊə(r)/` | `/əbˈskjʊər/` | W=C(US) |
| `obsession` | `/əbˈseʃ(ə)n/` | `/əbˈsɛʃən/` | W=I |
| `operator` | `/ˈɒpəreɪtə(r)/` | `/ˈɒpəˌɹeɪtə/` |  |
| `outdoor` | `/ˈaʊtdɔː(r)/` | `/ˈaʊtˌdɔːr/` | C=I |
| `outer` | `/ˈaʊtə(r)/` | `/ˈaʊtə/` |  |
| `owner` | `/ˈəʊnə(r)/` | `/ˈəʊnə/` | W=C(US) |
| `partner` | `/ˈpɑːtnə(r)/` | `/ˈpɑːt.nə(ɹ)/` | W=C(UK)|W=C(US) |
| `photographer` | `/fəˈtɒɡrəfə(r)/` | `/fəˈtɒɡ.ɹə.fə/` | W=C(US) |
| `picture` | `/ˈpɪktʃə(r)/` | `/ˈpɪk.t͡ʃə/` | W=C(US) |
| `poison` | `/ˈpɔɪz(ə)n/` | `/ˈpɔɪ.zən/` | W=I |
| `polar` | `/ˈpəʊlə(r)/` | `/ˈpəʊ.lə/` | W=C(US) |
| `poster` | `/ˈpəʊstə(r)/` | `/ˈpəʊ.stər/` | W=C(US) |
| `posture` | `/ˈpɒstʃə(r)/` | `/ˈpɒst͡ʃə/` | W=C(US) |
| `predictor` | `/prɪˈdɪktə(r)/` | `/pɹɪˈdɪk.tə/` | W=C(US) |
| `presents` | `/ˈprez(ə)nts/` | `/ˈpɹɛzənts/` | W=I |
| `prior` | `/ˈpraɪə(r)/` | `/ˈpɹaɪ.ə/` |  |
| `pure` | `/pjʊə(r)/` | `/pjʉːɹ/` | W=C(US) |
| `radiation` | `/ˌreɪdiˈeɪʃ(ə)n/` | `/ˌɹeɪ.diˈeɪ.ʃən/` | W=I |
| `reason` | `/ˈriːz(ə)n/` | `/ˈɹiːzən/` | W=I |
| `recover` | `/rɪˈkʌvə(r)/` | `/ɹɪˈkʌvə/` | W=C(US) |
| `registration` | `/ˌredʒɪˈstreɪʃ(ə)n/` | `/ˌɹɛd͡ʒ.ɪˈstɹeɪ.ʃən/` | W=I |
| `restore` | `/rɪˈstɔː(r)/` | `/ɹɪˈstoə/` | C=I |
| `retailer` | `/ˈriːteɪlə(r)/` | `/ˈriː.teɪ.lər/` | W=C(US) |
| `river` | `/ˈrɪvə(r)/` | `/ˈɹɪvəː/` | W=C(US) |
| `scar` | `/skɑː(r)/` | `/skɑː(ɹ)/` | W=C(UK)|W=I|C=I |
| `score` | `/skɔː(r)/` | `/skoə/` | C=I |
| `sculpture` | `/ˈskʌlptʃə(r)/` | `/ˈskʌlptj(ʊ)ə/` | W=C(US) |
| `senior` | `/ˈsiːniə(r)/` | `/ˈsiːnjə(ɹ)/` | W=C(US) |
| `seven` | `/ˈsev(ə)n/` | `/ˈsɛvən/` | W=I |
| `seventeenth` | `/ˌsev(ə)nˈtiːnθ/` | `/ˌsɛvənˈtiːnθ/` | W=I |
| `shore` | `/ʃɔː(r)/` | `/ʃoə/` | C=I |
| `speaker` | `/ˈspiːkə(r)/` | `/ˈspiːkə/` | W=C(US) |
| `sponsor` | `/ˈspɒnsə(r)/` | `/ˈspɒn.səː/` | W=C(US) |
| `spur` | `/spɜː(r)/` | `/spɜː/` | W=C(US) |
| `steer` | `/stɪə(r)/` | `/stɪə/` | W=C(US) |
| `store` | `/stɔː(r)/` | `/stoə/` | C=I |
| `strengthen` | `/ˈstreŋkθ(ə)n/` | `/ˈstɹɛŋ(k)θən/` |  |
| `summer` | `/ˈsʌmə(r)/` | `/ˈsʌmə/` | W=C(US) |
| `super` | `/ˈsuːpə(r)/` | `/ˈsuːpə/` | W=C(US) |
| `suspicion` | `/səˈspɪʃ(ə)n/` | `/səˈspɪʃ.ən/` | W=I |
| `tailor` | `/ˈteɪlə(r)/` | `/ˈteɪlə/` | W=C(US) |
| `teacher` | `/ˈtiːtʃə(r)/` | `/ˈtiː.t͡ʃəː/` | W=C(US) |
| `tower` | `/ˈtaʊə(r)/` | `/ˈtaʊ.ə(ɹ)/` | W=C(UK)|W=C(US) |
| `trigger` | `/ˈtrɪɡə(r)/` | `/ˈtɹɪɡəː/` | W=C(US) |
| `turnover` | `/ˈtɜːnəʊvə(r)/` | `/ˈtɜːnˌəʊ.vər/` | W=C(US) |
| `upper` | `/ˈʌpə(r)/` | `/ˈʌpə/` | W=C(US) |
| `vegetation` | `/ˌvedʒəˈteɪʃ(ə)n/` | `/ˌvɛd͡ʒəˈteɪʃən/` | W=I |
| `viewer` | `/ˈvjuːə(r)/` | `/ˈvjuːə/` | W=C(US) |
| `wander` | `/ˈwɒndə(r)/` | `/ˈwɒndə/` | W=C(US) |
| `war` | `/wɔː(r)/` | `/wɔː/` | W=C(US)|C=I |
| `wonder` | `/ˈwʌndə(r)/` | `/ˈwʌndə/` | W=C(US) |

## Medium-Priority: 24 Words with Cross-Source Disagreement

| Word | Current | Recommended | Sources |
|---|---|---|---|
| `abuse` | `/əˈbjuːz/` | `/əˈbjuːs/` | W=C(US)|W=I |
| `academia` | `/ˌækəˈdiːmiə/` | `/ˌæk.əˈdiː.mɪ.ə/` | W=C(US)|C=I |
| `constituency` | `/kənˈstɪtju.ənsi/` | `/kənˈstɪt͡ʃu.ənsi/` | W=C(UK)|W=I|C=I |
| `department` | `/dɪˈpɑːtmənt/` | `/dɪˈpɑːtm(ə)nt/` | W=C(UK)|W=C(US) |
| `enjoy` | `/ɪnˈdʒɔɪ/` | `/ɛnˈd͡ʒɔɪ/` | W=C(US)|W=I |
| `fruit` | `/fruːt/` | `/fɹʉwt/` | W=C(US)|C=I |
| `halt` | `/hɔːlt/` | `/hɒlt/` | W=C(UK)|W=C(US) |
| `harness` | `/ˈhɑːnɪs/` | `/ˈhɑː.nəs/` | W=C(UK)|W=C(US) |
| `historian` | `/hɪˈstɔːriən/` | `/hɪˈstɔːɹɪən/` | W=C(US)|C=I |
| `hydrogen` | `/ˈhaɪdrədʒən/` | `/ˈhaɪdɹəd͡ʒ(ə)n/` | W=C(UK)|W=I|C=I |
| `math` | `/mæθ/` | `/mɑːθ/` | W=C(US)|C=I |
| `module` | `/ˈmɒdjuːl/` | `/ˈmɒd͡ʒul/` | W=C(UK)|W=C(US) |
| `negotiate` | `/nɪˈɡəʊʃieɪt/` | `/nəˈɡəʊ.ʃi.eɪt/` | W=C(UK)|W=C(US) |
| `news` | `/njuːz/` | `/nuz/` | W=C(US)|C=I |
| `obey` | `/əˈbeɪ/` | `/əʊˈbeɪ/` | W=C(UK)|W=C(US) |
| `pavement` | `/ˈpeɪvmənt/` | `/ˈpeɪvm(ə)nt/` | W=C(UK)|W=I|C=I |
| `philosophy` | `/fəˈlɒsəfi/` | `/fɪˈlɒs.ə.fi/` | W=C(UK)|W=C(US) |
| `poetry` | `/ˈpəʊətri/` | `/ˈpəʊ.ɪ.tɹi/` | W=C(UK)|W=C(US) |
| `previous` | `/ˈpriːviəs/` | `/ˈpɹiː.vɪəs/` | W=C(US)|C=I |
| `research` | `/rɪˈsɜːtʃ/` | `/ɹiˈsɝt͡ʃ/` | W=C(US)|W=I |
| `room` | `/ruːm/` | `/ɹʊm/` | W=C(US)|C=I |
| `statement` | `/ˈsteɪtmənt/` | `/ˈsteɪtm(ə)nt/` | W=C(UK)|W=C(US)|W=I|C=I |
| `suit` | `/suːt/` | `/sjuːt/` | W=C(US)|C=I |
| `yearly` | `/ˈjɜːli/` | `/ˈjɪəli/` | W=C(UK)|W=C(US) |

## Phrases (803 words) — Out of Scope

Phrases (2+ words joined by space) are tracked separately:
- Many are idioms not in 3 sources (e.g. `in a sense`, `blood pressure`, `focus on`)
- Phrase policy: needs product decision on whether single-word IPA pipeline applies
- The 4 luo phrases already have manual overrides (added in 2026-06-16 earlier round)

## Limitations

- 5,874 words (~47%) have NO 2-source agreement
  - Wikt missing English section: ~40% of all words
  - Cross-dialect differences: most of the rest (RP vs GA vowel differences like cut-bux, cot-caught)
- Cambridge's UK/US distinction sometimes unclear (Cambridge always shows both, but with different vowel quality)
- ipa-dict is en_US only — provides no UK consensus partner for Wikt

## Next Steps

1. **Apply 130 unsafe fixes** — pure wins, no risk of being wrong (lenient 2-source consensus)
2. **Apply 24 disagreement fixes** — needs human spot-check on a few words first (e.g. `abuse` current `/əˈbjuːz/` vs consensus `/əˈbjuːs/` — actually `abuse` has multiple POS with different vowels, might be a false positive)
3. **Generate Azure TTS for new overrides** — same path as the luo round: synthesize + upload + production metadata verify
4. **Add phrases to phrase_policy review** — not blocking, separate track

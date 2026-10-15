# Privacy, data governance and US/EU applicability

Operator: **Zahidul Islam**. Contact [muhammadzahidulislam2222@gmail.com](mailto:muhammadzahidulislam2222@gmail.com). This document describes engineering facts and required legal assessment; it is not a certification or individualized legal opinion. The website's [privacy notice](https://vericommerce.zahidul-islam.com/privacy), [terms](https://vericommerce.zahidul-islam.com/terms) and [cookies information](https://vericommerce.zahidul-islam.com/cookies) govern visitor-facing explanations.

## Current data handling

| Data | Purpose / current treatment |
|---|---|
| Opaque access cookie and server token hash | Select temporary isolated workspace; configured12h expiry |
| Product/source/passages/revisions | Ingestion, current-evidence retrieval, lineage and changed-source invalidation |
| Drafts, citations, job/evaluation state | Durable work, approval/export and measured regression |
| Audit metadata | Action/entity/time; application audit excludes raw source/query text and cookie tokens |
| Rate-limit keys | Abuse bounds; hashed identifiers do not automatically become anonymous data |
| Browser storage | Browser workspace approvals; clearing it does not clear server state |
| Contact email | Visitor's mail application sends to operator; no hidden automatic form submission |

Search questions are processed to retrieve passages and are not stored as query text in application audit records. Source/imported text and resulting drafts are stored until cleanup. Technical edge/hosting logs may contain addresses and request metadata. The application has no configured advertising or behavioral-analytics integration; infrastructure-provider practices require their own review.

The worker purges expired workspace records and dependent live data. Expiry is not an immediate erasure guarantee across logs/backups. Log/backup retention periods, encryption-at-rest coverage and automated deletion across restored backups are not fully verified. Do not claim end-to-end encryption, fixed backup erasure deadlines or indefinite durable storage.

Use generated or explicitly permitted non-sensitive inputs. Do not upload customer records, health data, payment details, credentials or confidential merchant material. Current browser access offers no account recovery; loss of the cookie can prevent retrieval. Export needed content before expiry.

## Permissions, rights and takedown

Before importing or redistributing product descriptions, manuals, images, reviews or training rows, record ownership/license, permitted purposes, retention and any third-party restrictions. Public availability is not permission to republish or train. Generated imagery must not be used as evidence of real product characteristics or certifications.

Send privacy, access, correction, deletion or rights/takedown requests to the contact above. Include the affected page/source and enough non-secret context to locate it; never send session tokens or identity documents unsolicited. The operator must assess identity proportionately, applicable rights, legal holds, recipients and removal impact. No automated rights-request portal or guaranteed response deadline is currently implemented.

Future deletion must remove/invalidate source descendants across passages, vector indexes, graphs, caches, drafts, exports where controlled and training lineage. Maintain deletion tombstones for recovery. Removing a training row does not remove its influence from weights; retrain/discard affected adapters when required rather than claiming unverified unlearning.

## European Union assessment

GDPR applicability depends on processing and territorial scope, including relevant EU establishments and certain offering/monitoring involving people in the EU. Free access does not by itself establish an exemption. Assess actual targeting, roles and data flows rather than assuming that a foreign operator or small project is outside scope. [European Commission applicability](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en), [EDPB territorial-scope guidelines](https://www.edpb.europa.eu/documents/guideline/guidelines-32018-on-the-territorial-scope-of-the-gdpr-article-3-version-adopted_en).

For a merchant service, determine controller/processor responsibilities per processing purpose; document lawful basis, notices, minimization, retention, rights handling and security. Where processing for a merchant requires it, establish an Article 28 agreement, subprocessor terms and instructions. [European Commission controller/processor clauses](https://commission.europa.eu/publications/standard-contractual-clauses-controllers-and-processors-eueea_en). Assess international transfers, an appropriate transfer mechanism and supplementary measures; hosting abroad alone does not settle compliance.

Assess DPIA/DPO/representative duties where applicable. Review electronic communications/cookie rules before optional tracking or storage is introduced. Essential session storage and future analytics have different purposes; do not deploy a consent banner as a substitute for lawful processing or accurate notices.

Personal-data incidents require a documented risk assessment and jurisdiction-specific notification decision. GDPR Article 33 generally requires supervisory-authority notification where applicable within 72 hours of awareness unless unlikely to risk rights/freedoms, with reasons for delay; high-risk affected-person notification has its own test. Obtain competent legal support and do not wait for technical restoration before assessing notification. [EDPB breach guidance](https://www.edpb.europa.eu/sme/assess-the-risks/data-breaches_en).

## United States assessment

The US has federal sector-specific and state privacy/security rules, not one universal website privacy certification. The FTC emphasizes truthful privacy promises, data minimization and appropriate security. Review product/marketing claims, endorsements and any sensitive-data use against the actual service. [FTC privacy/security guidance](https://www.ftc.gov/business-guidance/privacy-security).

California obligations depend on applicable business definitions/thresholds and processing, not merely a website being reachable there. Assess rights/notices, sale/sharing and sensitive information against the current law; other states require separate analysis. Do not claim all US privacy requirements are met because the application has a privacy page. [California Attorney General CCPA guidance](https://oag.ca.gov/privacy/ccpa).

Assess children's-data rules if a service is directed to children or has relevant actual knowledge. The current interface is intended for business/product information and does not provide a children's-data consent system. [FTC COPPA guidance](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions).

## Release requirements before handling merchant/customer personal data

Complete a data map and retention schedule, contractual role/DPA and subprocessor review, rights/takedown workflow, transfer assessment, credential encryption/key management, incident notification process and independently tested deletion/restoration controls. Publish accurate operator disclosures where legally required; do not invent an office, registration, certification or governing jurisdiction.

The current source-grounded design supports provenance and human approval, but those controls alone do not establish privacy, advertising, accessibility or AI-regulatory compliance. Reassess obligations as generative models, recommendations, profiling, advertising or automated decisions are introduced.

## AI governance and product claims

Before adding generative chat, learned recommendations or training/distribution of adapted models, assess the actual system purpose, EU AI Act role and risk category. Obligations differ for system providers, deployers and general-purpose model providers; using an embedding model does not by itself settle that assessment. Review applicable transparency, generated-content disclosure, literacy, documentation and monitoring duties against the current implementation timeline. No exemption or risk classification is asserted here. [European Commission AI Act guidance](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai).

Keep model/dataset provenance, intended use, limitations and human approval visible. Never claim an image proves medical suitability, certification or performance, and never advertise accuracy or conversion gains from generated regression data. Permission to use a model is separate from permission to reuse its training material or a merchant’s content. Reassess obligations before introducing sensitive profiling or consequential automated decisions.

---
title: "MS Word to HTML: A Comprehensive Guide"
description: "Learn how to convert MS Word documents to clean HTML code efficiently. This guide covers various methods, tools, and best practices for seamless conversion."
pubDate: 2025-10-15
tags: ["MS Word", "HTML", "Conversion", "Web Development", "Productivity"]
author: "Probably AI"
backgroundColor: "#ffdeba"
theme: "light"
aiPrompt: "Stuff"
---

```javascript
#!/usr/bin/env node

/**
 * Word HTML Cleanup Script
 * Processes Word-exported HTML files and creates clean, semantic HTML modules
 */

import { readFile, writeFile, mkdir, access } from 'fs/promises';
import { join, dirname, basename, extname } from 'path';
import { fileURLToPath } from 'url';
import * as cheerio from 'cheerio';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Template token mappings
const TEMPLATE_TOKENS = {
  // Domain URLs
  'https://www.[domain][area].com': '{{DomainFront:[domain][area]}}',
  'https://accounts.apps.[domain].com/access/login': '{{DomainUrl}}',

  // Special characters (footnote markers)
  '*': '{{asterisk}}',
  '**': '{{asterisk-double}}',
  '***': '{{asterisk-triple}}',
  '†': '{{dagger}}',
  '††': '{{dagger-double}}',
  '†††': '{{dagger-triple}}',
  '‡': '{{double-dagger}}',
  '‡‡': '{{double-dagger-double}}',
  'Δ': '{{delta}}',
  'ΔΔ': '{{delta-double}}',
  'ΔΔΔ': '{{delta-triple}}',
  '#': '{{number-sign}}',
  '##': '{{number-sign-double}}',
  '###': '{{number-sign-triple}}',
  '+': '{{plus}}',
  '++': '{{plus-double}}',
  '+++': '{{plus-triple}}',
  '§': '{{section}}',
  '§§': '{{section-double}}',
  '∥': '{{false-double}}',
  '″': '{{prime-double}}'
};

class WordHTMLProcessor {
  constructor(sourceFilePath) {
    this.sourceFilePath = sourceFilePath;
    this.sourceDir = dirname(sourceFilePath);
    this.sourceFilename = basename(sourceFilePath);
    this.prefix = this.extractPrefix();
    this.outputDir = join(this.sourceDir, this.prefix.toLowerCase());
    this.faqSchemasDir = join(this.outputDir, 'faq-schemas');

    this.sections = [];
    this.faqPairs = new Map(); // Maps section name to FAQ pairs
    this.disclosures = [];
    this.tokenReplacements = [];
  }

  extractPrefix() {
    const nameWithoutExt = basename(this.sourceFilePath, extname(this.sourceFilePath));
    const firstUnderscore = nameWithoutExt.indexOf('_');
    return firstUnderscore > 0 ? nameWithoutExt.substring(0, firstUnderscore) : nameWithoutExt;
  }

  async process() {
    console.log(`\n🚀 Processing: ${this.sourceFilename}`);
    console.log(`📁 Output directory: ${this.outputDir}\n`);

    // Read source file
    const html = await readFile(this.sourceFilePath, 'utf-8');
    const $ = cheerio.load(html, { decodeEntities: true });

    // Step 1: Remove Word-specific elements
    this.removeWordArtifacts($);

    // Step 2: Convert escaped markup
    this.convertEscapedMarkup($);

    // Step 3: Extract sections and content
    this.extractSections($);

    // Step 4: Extract FAQ pairs
    this.extractFAQPairs($);

    // Step 5: Extract disclosures from comments
    this.extractDisclosures($);

    // Step 6: Create output directories
    await this.createDirectories();

    // Step 7: Process and write files
    await this.writeOutputFiles($);

    // Step 8: Write summary report
    await this.writeSummaryReport();

    console.log('\n✅ Processing complete!\n');
  }

  removeWordArtifacts($) {
    console.log('🧹 Removing Word artifacts...');

    // Remove style blocks
    $('style').remove();

    // Remove Word-specific elements
    $('o\\:p, v\\:*, w\\:*').remove();
    $('[class^="Mso"], [class^="Gr"]').removeAttr('class');
    $('a[name^="mscom"]').remove();

    // Remove Word comment artifacts
    $('a[name^="_msocom"]').remove();
    $('div[style*="mso-element:comment"]').remove();

    // Clean inline styles with mso- properties
    $('[style]').each((i, elem) => {
      const style = $(elem).attr('style');
      if (style && style.includes('mso-')) {
        // Remove mso-specific properties
        const cleanStyle = style
          .split(';')
          .filter(prop => !prop.trim().startsWith('mso-'))
          .join(';');

        if (cleanStyle.trim()) {
          $(elem).attr('style', cleanStyle);
        } else {
          $(elem).removeAttr('style');
        }
      }
    });

    // Remove all remaining inline styles (per requirements)
    $('[style]').removeAttr('style');
  }

  convertEscapedMarkup($) {
    console.log('🔄 Converting escaped HTML entities...');

    // Find all text nodes and unescape HTML
    const body = $('body');
    if (body.length) {
      let html = body.html();

      // Convert escaped HTML tags back to real tags
      html = html
        .replace(/&lt;(\/?)(h[1-6]|p|strong|em|ul|ol|li|a|br)([^&]*?)&gt;/gi, '<$1$2$3>')
        .replace(/&lt;a\s+([^&]+)&gt;/gi, '<a $1>')
        .replace(/&quot;/g, '"');

      body.html(html);
    }
  }

  extractSections($) {
    console.log('📑 Extracting sections...');

    const body = $('body');
    const html = body.html() || '';

    // Find all section markers [SECTION NAME]
    const sectionRegex = /\[([^\]]+)\]/g;
    let match;
    const sectionPositions = [];

    while ((match = sectionRegex.exec(html)) !== null) {
      sectionPositions.push({
        marker: match[0],
        name: match[1],
        start: match.index,
        end: match.index + match[0].length
      });
    }

    // Extract content between markers
    for (let i = 0; i < sectionPositions.length; i++) {
      const current = sectionPositions[i];
      const next = sectionPositions[i + 1];

      const contentStart = current.end;
      const contentEnd = next ? next.start : html.length;
      const content = html.substring(contentStart, contentEnd);

      // Load content into cheerio for processing
      const $content = cheerio.load(content);

      this.sections.push({
        marker: current.marker,
        name: current.name,
        content: $content.html(),
        index: i
      });
    }

    // Handle duplicate section names
    const nameCounts = {};
    this.sections.forEach(section => {
      const baseName = section.name;
      nameCounts[baseName] = (nameCounts[baseName] || 0) + 1;
    });

    // Add suffixes to duplicates
    const nameOccurrences = {};
    this.sections.forEach(section => {
      const baseName = section.name;
      if (nameCounts[baseName] > 1) {
        nameOccurrences[baseName] = (nameOccurrences[baseName] || 0) + 1;
        const letter = String.fromCharCode(96 + nameOccurrences[baseName]); // a, b, c...
        section.filename = this.toKebabCase(`${baseName}-${letter}`);
      } else {
        section.filename = this.toKebabCase(baseName);
      }
    });

    console.log(`   Found ${this.sections.length} sections`);
  }

  extractFAQPairs($) {
    console.log('❓ Extracting FAQ pairs...');

    // Pattern for Q&A markers: [Q1], [A1], [Q2], [A2], etc.
    const qMarkerRegex = /\[(Q|QS|GS)(\d+|[A-Z]+)\]/gi;
    const aMarkerRegex = /\[(A|AS)(\d+|[A-Z]+)\]/gi;

    this.sections.forEach(section => {
      const $section = cheerio.load(section.content);
      const html = $section.html() || '';

      // Find Q&A pairs
      const questions = [];
      const answers = [];

      // Extract questions
      let qMatch;
      while ((qMatch = qMarkerRegex.exec(html)) !== null) {
        const qStart = qMatch.index + qMatch[0].length;
        // Find the next marker or end
        const nextMatch = html.substring(qStart).search(/\[[QA]/i);
        const qEnd = nextMatch !== -1 ? qStart + nextMatch : html.length;

        questions.push({
          marker: qMatch[0],
          id: qMatch[2],
          content: html.substring(qStart, qEnd).trim()
        });
      }

      // Extract answers
      let aMatch;
      while ((aMatch = aMarkerRegex.exec(html)) !== null) {
        const aStart = aMatch.index + aMatch[0].length;
        const nextMatch = html.substring(aStart).search(/\[[QA]/i);
        const aEnd = nextMatch !== -1 ? aStart + nextMatch : html.length;

        answers.push({
          marker: aMatch[0],
          id: aMatch[2],
          content: html.substring(aStart, aEnd).trim()
        });
      }

      // Pair questions with answers
      const pairs = [];
      for (let i = 0; i < Math.min(questions.length, answers.length); i++) {
        if (questions[i] && answers[i]) {
          pairs.push({
            question: questions[i].content,
            answer: answers[i].content
          });
        }
      }

      if (pairs.length > 0) {
        this.faqPairs.set(section.filename, pairs);
        console.log(`   Found ${pairs.length} Q&A pairs in ${section.filename}`);
      }
    });
  }

  extractDisclosures($) {
    console.log('📋 Extracting disclosures...');

    // Word comments are typically in special divs or as comment nodes
    // This is a heuristic approach since Word HTML structure varies

    $('*').contents().each((i, node) => {
      if (node.type === 'comment') {
        const comment = node.data;

        // Look for disclosure patterns
        if (
          comment.includes('disclaimer') ||
          comment.includes('Dsvl:') ||
          comment.includes('disclosure') ||
          /\[([A-Z]{2,3})\]/.test(comment)
        ) {
          // Extract comment ID if present
          const idMatch = comment.match(/\[([A-Z]{2,3})\]/);
          const commentId = idMatch ? idMatch[1] : null;

          // Map comment ID to token
          const token = this.mapCommentIdToToken(commentId);

          this.disclosures.push({
            id: commentId,
            token: token,
            content: comment.trim()
          });
        }
      }
    });

    // Also check for disclosure text in paragraphs with specific patterns
    $('p, div').each((i, elem) => {
      const text = $(elem).text().trim();
      if (text.length > 100 && (
        text.toLowerCase().includes('disclaimer:') ||
        text.toLowerCase().includes('disclosure:') ||
        /^[†*§#\+‡Δ∥″]+/.test(text)
      )) {
        // Extract footnote marker
        const markerMatch = text.match(/^([†*§#\+‡Δ∥″]+)/);
        const marker = markerMatch ? markerMatch[1] : null;
        const token = TEMPLATE_TOKENS[marker] || null;

        this.disclosures.push({
          marker: marker,
          token: token,
          content: text
        });
      }
    });

    console.log(`   Found ${this.disclosures.length} disclosures`);
  }

  mapCommentIdToToken(commentId) {
    // Map comment IDs to common tokens (heuristic)
    const commonMappings = {
      'ESJ': '{{delta}}',
      'DSJ': '{{asterisk-double}}',
      'ASJ': '{{dagger}}',
    };
    return commonMappings[commentId] || '{{asterisk}}';
  }

  toKebabCase(str) {
    return str
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  async createDirectories() {
    console.log('📁 Creating output directories...');

    await mkdir(this.outputDir, { recursive: true });
    await mkdir(this.faqSchemasDir, { recursive: true });
  }

  async writeOutputFiles($) {
    console.log('📝 Writing output files...');

    // Process each section
    for (const section of this.sections) {
      const $section = cheerio.load(section.content);

      // Clean the content
      this.cleanSectionContent($section);

      // Apply template tokens
      let cleanHtml = $section.html();
      cleanHtml = this.applyTemplateTokens(cleanHtml);

      // Remove section markers from output
      cleanHtml = cleanHtml.replace(/\[([^\]]+)\]/g, '').trim();

      // Write main section file
      const outputPath = join(this.outputDir, `${section.filename}.html`);
      await writeFile(outputPath, cleanHtml, 'utf-8');
      console.log(`   ✓ ${section.filename}.html`);

      // Write FAQ schema file if this section has Q&As
      if (this.faqPairs.has(section.filename)) {
        await this.writeFAQSchema(section.filename);
      }
    }

    // Write disclosures file
    if (this.disclosures.length > 0) {
      await this.writeDisclosures();
    }
  }

  cleanSectionContent($) {
    // Improve semantic structure
    $('span').each((i, elem) => {
      const $elem = $(elem);
      const text = $elem.text().trim();

      // Convert spans to semantic elements based on content
      if (text.match(/^(chapter|section) \d+/i)) {
        const $h2 = $('<h2></h2>').html($elem.html());
        $elem.replaceWith($h2);
      } else if (text.length > 0 && !$elem.parent().is('p, li, h1, h2, h3, h4, h5, h6')) {
        const $p = $('<p></p>').html($elem.html());
        $elem.replaceWith($p);
      }
    });

    // Add classes to lists
    $('ul').addClass('bullets');
    $('ol').addClass('numbers');

    // Ensure strong tags include trailing colons
    $('strong').each((i, elem) => {
      const $elem = $(elem);
      const text = $elem.text();
      const $next = $elem.next();

      if ($next && $next[0] && $next[0].type === 'text') {
        const nextText = $next[0].data;
        if (nextText.startsWith(':')) {
          $elem.text(text + ':');
          $next[0].data = nextText.substring(1);
        }
      }
    });

    // Remove empty elements
    $('p, div, span').each((i, elem) => {
      if ($(elem).text().trim() === '' && $(elem).children().length === 0) {
        $(elem).remove();
      }
    });
  }

  applyTemplateTokens(html) {
    let processedHtml = html;

    // Sort tokens by length (longest first) to avoid partial replacements
    const sortedTokens = Object.entries(TEMPLATE_TOKENS)
      .sort((a, b) => b[0].length - a[0].length);

    for (const [value, token] of sortedTokens) {
      // Escape special regex characters
      const escapedValue = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(escapedValue, 'g');

      if (regex.test(processedHtml)) {
        const count = (processedHtml.match(regex) || []).length;
        processedHtml = processedHtml.replace(regex, token);

        if (count > 0) {
          this.tokenReplacements.push({
            token,
            value,
            count
          });
        }
      }
    }

    return processedHtml;
  }

  async writeFAQSchema(sectionFilename) {
    const pairs = this.faqPairs.get(sectionFilename);
    if (!pairs || pairs.length === 0) return;

    let faqHtml = '';

    pairs.forEach((pair, index) => {
      faqHtml += `<!-- Q&A-${index + 1} -->\n`;

      // Process question and answer through cheerio for cleaning
      const $q = cheerio.load(pair.question);
      const $a = cheerio.load(pair.answer);

      this.cleanSectionContent($q);
      this.cleanSectionContent($a);

      let questionHtml = $q.html().trim();
      let answerHtml = $a.html().trim();

      // Apply template tokens
      questionHtml = this.applyTemplateTokens(questionHtml);
      answerHtml = this.applyTemplateTokens(answerHtml);

      // Ensure question is in h2, answer in p or list
      if (!questionHtml.startsWith('<h2>')) {
        questionHtml = `<h2>${questionHtml}</h2>`;
      }

      faqHtml += `${questionHtml}\n${answerHtml}\n\n`;
    });

    const outputPath = join(this.faqSchemasDir, `${sectionFilename}.html`);
    await writeFile(outputPath, faqHtml.trim(), 'utf-8');
    console.log(`   ✓ faq-schemas/${sectionFilename}.html`);
  }

  async writeDisclosures() {
    let disclosureHtml = '';

    this.disclosures.forEach((disclosure, index) => {
      const id = disclosure.id || disclosure.marker || 'unknown';
      const token = disclosure.token || '';

      disclosureHtml += `<!-- Disclosure-${index + 1}: [${id}] Token: ${token} -->\n`;

      // Clean the disclosure content
      const $content = cheerio.load(disclosure.content);
      let cleanContent = $content.text().trim();

      // Apply template tokens
      cleanContent = this.applyTemplateTokens(cleanContent);

      disclosureHtml += `<p>${cleanContent}</p>\n\n`;
    });

    const outputPath = join(this.outputDir, 'disclosures.html');
    await writeFile(outputPath, disclosureHtml.trim(), 'utf-8');
    console.log(`   ✓ disclosures.html`);
  }

  async writeSummaryReport() {
    console.log('📊 Writing summary report...');

    let report = '# Summary Report\n\n';
    report += `## Source File\n\n`;
    report += `- **Filename:** ${this.sourceFilename}\n`;
    report += `- **Location:** Kept in original location\n`;
    report += `- **Output Directory:** ${this.outputDir}\n\n`;

    // Section signifiers
    report += '## Section Signifiers (as they appear in source document)\n\n';
    this.sections.forEach((section, index) => {
      report += `${index + 1}. ${section.marker}\n`;
    });
    report += '\n';

    // File mapping
    report += '## File Mapping\n\n';
    report += '| Section Signifier | Output Filename |\n';
    report += '|-------------------|------------------|\n';
    this.sections.forEach(section => {
      report += `| ${section.marker} | ${section.filename}.html |\n`;
    });
    report += '\n';

    // FAQ schema files
    if (this.faqPairs.size > 0) {
      report += '## FAQ Schema Files\n\n';
      report += '| Parent Section | FAQ Schema File | Q&A Pairs |\n';
      report += '|----------------|-----------------|------------|\n';
      for (const [filename, pairs] of this.faqPairs.entries()) {
        const section = this.sections.find(s => s.filename === filename);
        const marker = section ? section.marker : filename;
        report += `| ${marker} | faq-schemas/${filename}.html | ${pairs.length} Q&As |\n`;
      }
      report += '\n';
    }

    // Disclosures
    if (this.disclosures.length > 0) {
      report += '## Disclosures\n\n';
      report += '| Disclosure | Token | ID/Marker |\n';
      report += '|------------|-------|-----------|\n';
      this.disclosures.forEach((disclosure, index) => {
        const id = disclosure.id || disclosure.marker || 'N/A';
        const token = disclosure.token || 'N/A';
        report += `| Disclosure-${index + 1} | ${token} | ${id} |\n`;
      });
      report += '\n';
    }

    // Token replacements
    if (this.tokenReplacements.length > 0) {
      report += '## Template Tokens Applied\n\n';
      const grouped = this.tokenReplacements.reduce((acc, item) => {
        if (!acc[item.token]) {
          acc[item.token] = { value: item.value, count: 0 };
        }
        acc[item.token].count += item.count;
        return acc;
      }, {});

      for (const [token, data] of Object.entries(grouped)) {
        report += `- ${token}: Replaced "${data.value}" (${data.count} occurrence${data.count > 1 ? 's' : ''})\n`;
      }
      report += '\n';
    }

    // Processing notes
    report += '## Processing Notes\n\n';
    report += `- Sections processed: ${this.sections.length}\n`;
    report += `- FAQ schema files: ${this.faqPairs.size}\n`;
    report += `- Disclosures extracted: ${this.disclosures.length}\n`;
    report += `- Template tokens applied: ${this.tokenReplacements.length}\n`;

    const reportPath = join(this.outputDir, 'summary-report.md');
    await writeFile(reportPath, report, 'utf-8');
    console.log(`   ✓ summary-report.md`);
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log(`
Word HTML Cleanup Script
========================

Usage: node word-html-cleanup.js <input-file.htm>

Example:
  node word-html-cleanup.js ./PCM021_[area]_Insurance.htm

This will create a directory named after the file prefix (e.g., 'pcm021/')
with cleaned HTML files, FAQ schemas, disclosures, and a summary report.
    `);
    process.exit(1);
  }

  const inputFile = args[0];

  try {
    // Check if file exists
    await access(inputFile);

    const processor = new WordHTMLProcessor(inputFile);
    await processor.process();

  } catch (error) {
    if (error.code === 'ENOENT') {
      console.error(`❌ Error: File not found: ${inputFile}`);
    } else {
      console.error(`❌ Error processing file:`, error.message);
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();
```
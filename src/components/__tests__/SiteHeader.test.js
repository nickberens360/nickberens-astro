// src/components/__tests__/SiteHeader.test.js

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import SiteHeader from '../SiteHeader.vue';

// Mock the stores
vi.mock('../../stores/ui', () => ({
  navItems: {
    get: () => [
      { text: 'nick.AI', url: '/nick-ai' },
      { text: 'Illustrations', url: '/illustrations' },
      { text: 'Atomic Docs', url: '/atomic-docs' },
      { text: 'Resume', url: '/resume' },
      { text: 'Contact', url: '/#contact' },
      {
        text: 'GitHub',
        url: 'https://github.com/nickberens360',
        isExternal: true,
        icon: ['fab', 'github'],
        ariaLabel: 'GitHub Profile'
      }
    ]
  },
  isTerminalHiddenStore: {
    get: () => false
  },
  isTerminalMinimizedStore: {
    get: () => true
  }
}));

// Mock @nanostores/vue
vi.mock('@nanostores/vue', () => ({
  useStore: (store) => store.get()
}));

// Mock FontAwesome component
const FontAwesomeIcon = {
  name: 'FontAwesomeIcon',
  props: ['icon', 'size'],
  template: '<span class="fa-icon">{{ icon }}</span>'
};

describe('SiteHeader.vue', () => {
  beforeEach(() => {
    // Mock browser APIs that aren't available in jsdom
    Object.defineProperty(document, 'elementFromPoint', {
      value: vi.fn(() => null),
      writable: true
    });

    // Mock window.addEventListener and removeEventListener
    Object.defineProperty(window, 'addEventListener', {
      value: vi.fn(),
      writable: true
    });

    Object.defineProperty(window, 'removeEventListener', {
      value: vi.fn(),
      writable: true
    });
  });

  it('renders correctly with navigation links', () => {
    // 1. Mount the component
    const wrapper = mount(SiteHeader, {
      global: {
        components: {
          FontAwesomeIcon
        },
        stubs: {
          TerminalInput: true
        }
      }
    });

    // 2. Assert that the component's root element exists
    expect(wrapper.exists()).toBe(true);

    // 3. Check that the site name/logo is present
    const siteName = wrapper.find('.site-header__name');
    expect(siteName.exists()).toBe(true);
    expect(siteName.text()).toContain('nickberens');

    // 4. Find the navigation links
    const nav = wrapper.find('.site-header__nav');
    expect(nav.exists()).toBe(true);

    const links = wrapper.findAll('nav a');
    expect(links.length).toBeGreaterThan(0);

    // 5. Check for specific navigation links based on the actual store data
    const nickAiLink = wrapper.find('a[href="/nick-ai"]');
    expect(nickAiLink.exists()).toBe(true);
    expect(nickAiLink.text()).toContain('nick.AI');

    const illustrationsLink = wrapper.find('a[href="/illustrations"]');
    expect(illustrationsLink.exists()).toBe(true);
    expect(illustrationsLink.text()).toContain('Illustrations');

    const atomicDocsLink = wrapper.find('a[href="/atomic-docs"]');
    expect(atomicDocsLink.exists()).toBe(true);
    expect(atomicDocsLink.text()).toContain('Atomic Docs');

    const resumeLink = wrapper.find('a[href="/resume"]');
    expect(resumeLink.exists()).toBe(true);
    expect(resumeLink.text()).toContain('Resume');

    const contactLink = wrapper.find('a[href="/#contact"]');
    expect(contactLink.exists()).toBe(true);
    expect(contactLink.text()).toContain('Contact');

    // 6. Check for external GitHub link
    const githubLink = wrapper.find('a[href="https://github.com/nickberens360"]');
    expect(githubLink.exists()).toBe(true);
    expect(githubLink.attributes('target')).toBe('_blank');
    expect(githubLink.attributes('rel')).toBe('noopener noreferrer');
    expect(githubLink.attributes('aria-label')).toBe('GitHub Profile');
  });

  it('renders the logo link correctly', () => {
    const wrapper = mount(SiteHeader, {
      global: {
        components: {
          FontAwesomeIcon
        },
        stubs: {
          TerminalInput: true
        }
      }
    });

    // Check that the logo link points to home
    const logoLink = wrapper.find('.site-header__logo a[href="/"]');
    expect(logoLink.exists()).toBe(true);
  });

  it('displays git branch information', () => {
    const wrapper = mount(SiteHeader, {
      props: {
        gitBranch: 'main'
      },
      global: {
        components: {
          FontAwesomeIcon
        },
        stubs: {
          TerminalInput: true
        }
      }
    });

    const gitBranch = wrapper.find('.git-branch');
    expect(gitBranch.exists()).toBe(true);
    expect(gitBranch.text()).toBe('main');
  });
});
import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import AnnoyingEyelash from '../AnnoyingEyelash.vue';
import { resetEasterEggs, easterEggsStore } from '../../stores/easter-eggs.js';

describe('AnnoyingEyelash', () => {
  beforeEach(() => {
    // Reset the store before each test
    resetEasterEggs();
  });

  it('should use props when no stored position exists', async () => {
    const wrapper = mount(AnnoyingEyelash, {
      props: {
        initialX: 100,
        initialY: 200
      }
    });

    // Wait for component to mount and update store
    await wrapper.vm.$nextTick();

    const storeState = easterEggsStore.get();
    expect(storeState.annoyingEyelash.currentX).toBe(100);
    expect(storeState.annoyingEyelash.currentY).toBe(200);
    expect(storeState.annoyingEyelash.isVisible).toBe(true);
  });

  it('should use stored position after mount', async () => {
    // Set a position in the store first
    const storeState = easterEggsStore.get();
    easterEggsStore.set({
      ...storeState,
      annoyingEyelash: {
        ...storeState.annoyingEyelash,
        currentX: 300,
        currentY: 400
      }
    });

    const wrapper = mount(AnnoyingEyelash, {
      props: {
        initialX: 100,
        initialY: 200
      }
    });

    // Initially should use props (for hydration)
    const eyelashElement = wrapper.find('.annoying-eyelash');
    expect(eyelashElement.element.style.left).toBe('100px');
    expect(eyelashElement.element.style.top).toBe('200px');

    // After mount, should switch to stored position
    await wrapper.vm.$nextTick();
    expect(eyelashElement.element.style.left).toBe('300px');
    expect(eyelashElement.element.style.top).toBe('400px');
  });

  it('should update drag attempts in store', async () => {
    const wrapper = mount(AnnoyingEyelash);

    // Simulate drag start
    const eyelashElement = wrapper.find('.annoying-eyelash');
    await eyelashElement.trigger('pointerdown', {
      isPrimary: true,
      clientX: 100,
      clientY: 100
    });

    const storeState = easterEggsStore.get();
    expect(storeState.annoyingEyelash.dragAttempts).toBe(1);
  });

  it('should hide when hideAnnoyingEyelash prop is true', () => {
    const wrapper = mount(AnnoyingEyelash, {
      props: {
        hideAnnoyingEyelash: true
      }
    });

    expect(wrapper.find('.annoying-eyelash').exists()).toBe(false);
  });
});

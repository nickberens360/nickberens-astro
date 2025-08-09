import { atom } from 'nanostores';

// Navigation items store
export const navItems = atom([
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
]);

// Image overlay state
export const imageOverlayStore = atom({
  isOpen: false,
  imageSrc: null
});

// Helper functions to open and close the overlay
export const openImageOverlay = (src) => {
  imageOverlayStore.set({
    isOpen: true,
    imageSrc: src
  });
};

export const closeImageOverlay = () => {
  imageOverlayStore.set({
    isOpen: false,
    imageSrc: null
  });
};
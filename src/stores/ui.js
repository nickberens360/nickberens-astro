import { atom } from 'nanostores';

// Font items store - will be populated dynamically
export const fontItems = atom([]);

// Navigation items store
export const navItems = atom([
  { text: 'nick.AI', url: '/nick-ai' },
  { text: 'Illustrations', url: '/illustrations' },
  { text: 'Atomic Docs', url: '/atomic-docs' },
  {
    text: 'Fonts',
    url: '#',
    hasDropdown: true,
    dropdownItems: [] // Will be populated from fontItems
  },
  { text: 'Resume', url: '/resume' },
 // { text: 'Contact', url: '/#contact' },
  {
    text: 'GitHub',
    url: 'https://github.com/nickberens360',
    isExternal: true,
    icon: ['fab', 'github'],
    ariaLabel: 'GitHub Profile'
  }
]);

// Helper function to update font items
export const updateFontItems = (fonts) => {
  console.log('updateFontItems called with:', fonts);
  const fontMenuItems = fonts.map(font => {
    // For Astro content collections, font.id is the filename without extension
    // font.data contains the actual JSON content
    const fontId = font.id || font.slug || 'unknown';
    const fontName = font.data?.name || font.name || 'Unknown Font';
    const menuItem = {
      text: fontName,
      url: `/fonts/${fontId}`
    };
    console.log(`Creating menu item: ${fontName} -> /fonts/${fontId}`);
    return menuItem;
  });

  console.log('Generated fontMenuItems:', fontMenuItems);
  fontItems.set(fontMenuItems);

  // Update the navItems with the new font dropdown items
  const currentNavItems = navItems.get();

  const updatedNavItems = currentNavItems.map(item => {
    if (item.text === 'Fonts') {
      const updated = { ...item, dropdownItems: fontMenuItems };
      console.log('Updated Fonts nav item:', updated);
      return updated;
    }
    return item;
  });

  navItems.set(updatedNavItems);
  console.log('Final navItems:', navItems.get());
};

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
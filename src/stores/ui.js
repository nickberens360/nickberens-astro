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
  { text: 'Contact', url: '/#contact' },
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
  console.log('updateFontItems: Called with fonts:', fonts);
  
  const fontMenuItems = fonts.map(font => {
    console.log('updateFontItems: Processing font:', font);
    const menuItem = {
      text: font.data?.name || font.name || 'Unknown Font',
      url: `/fonts/${font.id || font.slug || 'unknown'}`
    };
    console.log('updateFontItems: Created menu item:', menuItem);
    return menuItem;
  });
  
  console.log('updateFontItems: Final font menu items:', fontMenuItems);
  fontItems.set(fontMenuItems);
  
  // Update the navItems with the new font dropdown items
  const currentNavItems = navItems.get();
  console.log('updateFontItems: Current nav items:', currentNavItems);
  
  const updatedNavItems = currentNavItems.map(item => {
    if (item.text === 'Fonts') {
      const updated = { ...item, dropdownItems: fontMenuItems };
      console.log('updateFontItems: Updated Fonts item:', updated);
      return updated;
    }
    return item;
  });
  
  console.log('updateFontItems: Final nav items:', updatedNavItems);
  navItems.set(updatedNavItems);
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
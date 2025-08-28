import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import {
  // Navigation & Core
  mdiHome, mdiViewDashboard, mdiMagnify, mdiChartLine, mdiFileDocument,
  mdiAccountGroup, mdiAccount, mdiMenu, mdiClose, mdiRefresh, mdiExport,
  
  // Actions & Controls
  mdiLock, mdiLockOutline, mdiLockCheck, mdiLogout, mdiFilter, mdiEye,
  mdiDownload, mdiUpload, mdiCloudUpload, mdiPaperclip, mdiDelete,
  mdiPencil, mdiNoteEdit, mdiUndo,
  
  // Status & Feedback
  mdiAlert, mdiCheck, mdiCheckCircle, mdiClockOutline, mdiTrendingUp,
  mdiTrendingDown, mdiThumbUpOutline, mdiThumbUp, mdiThumbDown,
  mdiAlertCircleOutline,
  
  // Content & Knowledge
  mdiBookOpenPageVariant, mdiInformation, mdiFolder, mdiFormatListBulleted,
  mdiCodeBraces, mdiFilePdfBox, mdiFileDocumentOutline, mdiTextBox, mdiWeb, mdiHelpCircleOutline,
  
  // Theme & System
  mdiWeatherNight, mdiWhiteBalanceSunny, mdiMemory, mdiChartBar,
  mdiLightbulbOutline, mdiLightbulb, mdiTableLarge
} from '@mdi/js'

// Import Vuetify styles
import 'vuetify/styles'

// Theme configurations
const themes = {
  light: {
    dark: false,
    colors: {
      primary: '#1976D2',
      secondary: '#424242',
      accent: '#82B1FF',
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
      surface: '#FFFFFF',
      background: '#F5F5F5'
    }
  },
  dark: {
    dark: true,
    colors: {
      primary: '#2196F3',
      secondary: '#616161',
      accent: '#82B1FF',
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
      surface: '#1E1E1E',
      background: '#121212'
    }
  }
}

// Custom typography configuration for Vuetify
const typography = {
  fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
  h1: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1.875rem',
    fontWeight: 700,
    lineHeight: '1.3',
    letterSpacing: '0em'
  },
  h2: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1.5rem',
    fontWeight: 600,
    lineHeight: '1.4',
    letterSpacing: '0em'
  },
  h3: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1.25rem',
    fontWeight: 600,
    lineHeight: '1.4',
    letterSpacing: '0em'
  },
  h4: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1.125rem',
    fontWeight: 500,
    lineHeight: '1.4',
    letterSpacing: '0em'
  },
  h5: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: '1.5',
    letterSpacing: '0em'
  },
  h6: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: '1.5',
    letterSpacing: '0.01em'
  },
  subtitle1: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: '1.6',
    letterSpacing: '0em'
  },
  subtitle2: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: '1.4',
    letterSpacing: '0.01em'
  },
  body1: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: '1.6',
    letterSpacing: '0em'
  },
  body2: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.875rem',
    fontWeight: 400,
    lineHeight: '1.5',
    letterSpacing: '0em'
  },
  button: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: '1.6',
    letterSpacing: '0.01em',
    textTransform: 'none' // Remove uppercase transformation
  },
  caption: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: '1.5',
    letterSpacing: '0.01em'
  },
  overline: {
    fontFamily: '"JetBrains Mono", "SF Mono", Monaco, Inconsolata, "Source Code Pro", Consolas, "Courier New", monospace',
    fontSize: '0.75rem',
    fontWeight: 500,
    lineHeight: '1.5',
    letterSpacing: '0.05em',
    textTransform: 'uppercase'
  }
}

// Icon aliases configuration
const iconAliases = {
  // Navigation
  home: mdiHome,
  dashboard: mdiViewDashboard,
  search: mdiMagnify,
  chart: mdiChartLine,
  document: mdiFileDocument,
  users: mdiAccountGroup,
  knowledge: mdiBookOpenPageVariant,
  
  // Actions
  menu: mdiMenu,
  close: mdiClose,
  refresh: mdiRefresh,
  export: mdiExport,
  filter: mdiFilter,
  view: mdiEye,
  download: mdiDownload,
  upload: mdiUpload,
  'cloud_upload': mdiCloudUpload,
  'attach_file': mdiPaperclip,
  delete: mdiDelete,
  edit: mdiPencil,
  'note-edit': mdiNoteEdit,
  undo: mdiUndo,
  
  // Status
  alert: mdiAlert,
  check: mdiCheck,
  'check-circle': mdiCheckCircle,
  'check_circle': mdiCheckCircle,
  clock: mdiClockOutline,
  schedule: mdiClockOutline,
  trendUp: mdiTrendingUp,
  trendDown: mdiTrendingDown,
  'thumb-up-outline': mdiThumbUpOutline,
  'thumb-up': mdiThumbUp,
  'thumb-down': mdiThumbDown,
  warning: mdiAlertCircleOutline,
  
  // Content types
  info: mdiInformation,
  folder: mdiFolder,
  list: mdiFormatListBulleted,
  description: mdiFileDocument,
  'data_object': mdiCodeBraces,
  'picture_as_pdf': mdiFilePdfBox,
  'text_snippet': mdiTextBox,
  language: mdiWeb,
  article: mdiFileDocumentOutline,
  'insert_drive_file': mdiFileDocumentOutline,
  help: mdiHelpCircleOutline,
  
  // User & Security
  account: mdiAccount,
  lock: mdiLock,
  'lock-outline': mdiLockOutline,
  'lock-check': mdiLockCheck,
  logout: mdiLogout,
  
  // Theme
  'weather-night': mdiWeatherNight,
  'light-mode': mdiWhiteBalanceSunny,
  
  // System
  memory: mdiMemory,
  'bar_chart': mdiChartBar,
  lightbulb: mdiLightbulbOutline,
  recommend: mdiLightbulb,
  table: mdiTableLarge
}

export default createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes,
    variations: {
      colors: ['primary', 'secondary', 'accent', 'error', 'info', 'success', 'warning'],
      lighten: 5,
      darken: 5
    }
  },
  typography,
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...aliases,
      ...iconAliases
    },
    sets: { mdi }
  },
  defaults: {
    VCard: {
      elevation: 2,
      rounded: 'lg'
    },
    VBtn: {
      variant: 'flat',
      rounded: 'lg'
    },
    VDataTable: {
      itemsPerPage: 25,
      hover: true
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable'
    },
    // Typography defaults for common components
    VCardTitle: {
      class: 'typography-h5'
    },
    VCardText: {
      class: 'typography-body-1'
    },
    VListItemTitle: {
      class: 'typography-body-1 font-medium'
    },
    VListItemSubtitle: {
      class: 'typography-body-2'
    },
    VChip: {
      class: 'typography-caption font-medium'
    }
  }
})
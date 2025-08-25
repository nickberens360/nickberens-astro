import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { 
  mdiHome, 
  mdiViewDashboard, 
  mdiMagnify, 
  mdiChartLine, 
  mdiFileDocument,
  mdiAccountGroup,
  mdiAccount,
  mdiLock,
  mdiLockOutline,
  mdiLockCheck,
  mdiLogout,
  mdiMenu,
  mdiClose,
  mdiRefresh,
  mdiExport,
  mdiFilter,
  mdiEye,
  mdiDownload,
  mdiAlert,
  mdiCheck,
  mdiCheckCircle,
  mdiClockOutline,
  mdiTrendingUp,
  mdiTrendingDown,
  mdiThumbUpOutline,
  mdiThumbUp,
  mdiThumbDown,
  mdiBookOpenPageVariant,
  mdiUpload,
  mdiCloudUpload,
  mdiPaperclip,
  mdiInformation,
  mdiFolder,
  mdiFormatListBulleted,
  mdiDelete,
  mdiCodeBraces,
  mdiFilePdfBox,
  mdiFileDocumentOutline,
  mdiTextBox,
  mdiWeb,
  mdiPencil,
  mdiNoteEdit,
  mdiUndo,
  mdiWeatherNight,
  mdiWhiteBalanceSunny,
  mdiMemory
} from '@mdi/js'

// Import Vuetify styles
import 'vuetify/styles'

// Light theme
const lightTheme = {
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
}

// Dark theme
const darkTheme = {
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

export default createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes: {
      light: lightTheme,
      dark: darkTheme
    }
  },
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...aliases,
      home: mdiHome,
      dashboard: mdiViewDashboard,
      search: mdiMagnify,
      chart: mdiChartLine,
      document: mdiFileDocument,
      users: mdiAccountGroup,
      knowledge: mdiBookOpenPageVariant,
      upload: mdiUpload,
      'cloud_upload': mdiCloudUpload,
      'attach_file': mdiPaperclip,
      info: mdiInformation,
      folder: mdiFolder,
      list: mdiFormatListBulleted,
      schedule: mdiClockOutline,
      description: mdiFileDocument,
      delete: mdiDelete,
      menu: mdiMenu,
      close: mdiClose,
      refresh: mdiRefresh,
      export: mdiExport,
      filter: mdiFilter,
      view: mdiEye,
      download: mdiDownload,
      alert: mdiAlert,
      check: mdiCheck,
      'check-circle': mdiCheckCircle,
      clock: mdiClockOutline,
      trendUp: mdiTrendingUp,
      trendDown: mdiTrendingDown,
      'thumb-up-outline': mdiThumbUpOutline,
      'thumb-up': mdiThumbUp,
      'thumb-down': mdiThumbDown,
      'data_object': mdiCodeBraces,
      'picture_as_pdf': mdiFilePdfBox,
      'text_snippet': mdiTextBox,
      'language': mdiWeb,
      'article': mdiFileDocumentOutline,
      'insert_drive_file': mdiFileDocumentOutline,
      edit: mdiPencil,
      'note-edit': mdiNoteEdit,
      undo: mdiUndo,
      account: mdiAccount,
      lock: mdiLock,
      'lock-outline': mdiLockOutline,
      'lock-check': mdiLockCheck,
      logout: mdiLogout,
      'weather-night': mdiWeatherNight,
      'light-mode': mdiWhiteBalanceSunny,
      memory: mdiMemory
    },
    sets: {
      mdi
    }
  },
  defaults: {
    VCard: {
      elevation: 2
    },
    VBtn: {
      variant: 'flat'
    },
    VDataTable: {
      itemsPerPage: 25
    }
  }
})
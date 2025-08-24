import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { 
  mdiHome, 
  mdiViewDashboard, 
  mdiMagnify, 
  mdiChartLine, 
  mdiFileDocument,
  mdiAccountGroup,
  mdiMenu,
  mdiClose,
  mdiRefresh,
  mdiExport,
  mdiFilter,
  mdiEye,
  mdiDownload,
  mdiAlert,
  mdiCheck,
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
  mdiPencil
} from '@mdi/js'

// Import Vuetify styles
import 'vuetify/styles'

// Custom theme
const customTheme = {
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

export default createVuetify({
  theme: {
    defaultTheme: 'customTheme',
    themes: {
      customTheme
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
      edit: mdiPencil
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
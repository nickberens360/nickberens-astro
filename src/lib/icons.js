// Central icon registration file for Font Awesome icons
import { library } from '@fortawesome/fontawesome-svg-core';
import {
  faGithub,
  faTwitter,
  faLinkedin,

} from '@fortawesome/free-brands-svg-icons';

import {
  faTerminal,
  faBars,
} from '@fortawesome/free-solid-svg-icons';


library.add(
  faGithub,
  faTwitter,
  faLinkedin,
  faTerminal,
  faBars
);

export { library };

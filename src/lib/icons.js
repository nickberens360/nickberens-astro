// Central icon registration file for Font Awesome icons
import { library } from '@fortawesome/fontawesome-svg-core';
import { 
    faGithub,
    faTwitter,
    faLinkedin,

} from '@fortawesome/free-brands-svg-icons';

import {
    faTerminal,
} from '@fortawesome/free-solid-svg-icons';


library.add(
    faGithub,
    faTwitter,
    faLinkedin,
    faTerminal,
);

export { library };

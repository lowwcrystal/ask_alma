import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const SEO = ({ title, description, keywords, image, path, type = 'website' }) => {
  // useLocation must be called unconditionally - component is always within Router context
  const location = useLocation();
  
  const siteUrl = 'https://askalmaai.com';
  const defaultTitle = 'AskAlma - Your AI Academic Advisor for Columbia University';
  const defaultDescription = 'Get instant answers about courses, registration, Core Curriculum, and more. Your intelligent AI academic advisor for Columbia, SEAS, and Barnard students.';
  const defaultImage = `${siteUrl}/Icon.png`;
  const defaultKeywords = 'Columbia University, AI advisor, academic advisor, course registration, Core Curriculum, Columbia College, SEAS, Barnard, course planning, academic help, Columbia courses, professor reviews, major requirements, semester planning';

  const fullTitle = title ? `${title} | ${defaultTitle}` : defaultTitle;
  const fullDescription = description || defaultDescription;
  const fullImage = image || defaultImage;
  const fullPath = path || (location?.pathname || '/');
  const fullUrl = `${siteUrl}${fullPath}`;
  const fullKeywords = keywords || defaultKeywords;

  useEffect(() => {
    // Safety check: only run in browser environment
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    // Update document title
    document.title = fullTitle;

    // Update or create meta tags
    const updateMetaTag = (name, content, isProperty = false) => {
      if (!content) return;
      const attribute = isProperty ? 'property' : 'name';
      let element = document.querySelector(`meta[${attribute}="${name}"]`);
      
      if (!element) {
        element = document.createElement('meta');
        element.setAttribute(attribute, name);
        document.head.appendChild(element);
      }
      
      element.setAttribute('content', content);
    };

    // Primary meta tags
    updateMetaTag('title', fullTitle);
    updateMetaTag('description', fullDescription);
    updateMetaTag('keywords', fullKeywords);
    updateMetaTag('author', 'AskAlma');
    updateMetaTag('robots', 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1');
    updateMetaTag('googlebot', 'index, follow');
    updateMetaTag('language', 'English');
    updateMetaTag('revisit-after', '7 days');
    updateMetaTag('rating', 'general');
    updateMetaTag('distribution', 'global');

    // Open Graph tags (Facebook, LinkedIn, etc.)
    updateMetaTag('og:title', fullTitle, true);
    updateMetaTag('og:description', fullDescription, true);
    updateMetaTag('og:url', fullUrl, true);
    updateMetaTag('og:image', fullImage, true);
    updateMetaTag('og:image:width', '1200', true);
    updateMetaTag('og:image:height', '630', true);
    updateMetaTag('og:image:alt', fullTitle, true);
    updateMetaTag('og:type', type, true);
    updateMetaTag('og:site_name', 'AskAlma', true);
    updateMetaTag('og:locale', 'en_US', true);

    // Twitter Card tags
    updateMetaTag('twitter:card', 'summary_large_image', true);
    updateMetaTag('twitter:title', fullTitle, true);
    updateMetaTag('twitter:description', fullDescription, true);
    updateMetaTag('twitter:image', fullImage, true);
    updateMetaTag('twitter:image:alt', fullTitle, true);
    updateMetaTag('twitter:site', '@AskAlma', true);
    updateMetaTag('twitter:creator', '@AskAlma', true);

    // Additional meta tags
    updateMetaTag('theme-color', '#003865');
    updateMetaTag('apple-mobile-web-app-capable', 'yes');
    updateMetaTag('apple-mobile-web-app-status-bar-style', 'black-translucent');
    updateMetaTag('apple-mobile-web-app-title', 'AskAlma');

    // Canonical URL
    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', fullUrl);

    // Remove old structured data scripts
    const oldScripts = document.querySelectorAll('script[type="application/ld+json"]');
    oldScripts.forEach(script => script.remove());

    // WebApplication Structured Data
    const webAppData = {
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: 'AskAlma',
      description: fullDescription,
      url: siteUrl,
      applicationCategory: 'EducationalApplication',
      operatingSystem: 'Web',
      browserRequirements: 'Requires JavaScript. Requires HTML5.',
      softwareVersion: '1.0',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        availability: 'https://schema.org/InStock'
      },
      creator: {
        '@type': 'Organization',
        name: 'AskAlma',
        url: siteUrl
      },
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
        audienceType: 'College Students',
        geographicArea: {
          '@type': 'City',
          name: 'New York'
        }
      },
      featureList: [
        'AI Academic Advisor',
        'Course Information',
        'Professor Reviews',
        'Major/Minor Requirements',
        'Semester Planning',
        'Core Curriculum Guidance',
        'Registration Help'
      ],
      screenshot: fullImage,
      inLanguage: 'en-US'
    };

    // Organization Structured Data
    const organizationData = {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: 'AskAlma',
      url: siteUrl,
      logo: fullImage,
      description: fullDescription,
      sameAs: [],
      contactPoint: {
        '@type': 'ContactPoint',
        contactType: 'Customer Service',
        availableLanguage: 'English'
      }
    };

    // Educational Organization (Columbia University reference)
    const educationalOrgData = {
      '@context': 'https://schema.org',
      '@type': 'EducationalOrganization',
      name: 'Columbia University',
      url: 'https://www.columbia.edu',
      description: 'Columbia University in the City of New York'
    };

    // Create and append structured data scripts
    const createScript = (data) => {
      const script = document.createElement('script');
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(data);
      document.head.appendChild(script);
    };

    createScript(webAppData);
    createScript(organizationData);
    createScript(educationalOrgData);

    // FAQ Structured Data (if on landing page)
    // Use fullPath which is already in dependency array (derived from location.pathname)
    if (fullPath === '/' || fullPath === '') {
      const faqData = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: [
          {
            '@type': 'Question',
            name: 'What is AskAlma?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'AskAlma is an AI-powered academic advisor for Columbia University students. It helps with course planning, registration, Core Curriculum requirements, and provides information about professors and academic policies.'
            }
          },
          {
            '@type': 'Question',
            name: 'Which schools does AskAlma support?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'AskAlma supports Columbia College, SEAS (School of Engineering and Applied Science), and Barnard College students.'
            }
          },
          {
            '@type': 'Question',
            name: 'Is AskAlma free to use?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'Yes, AskAlma is completely free to use for all Columbia University students.'
            }
          },
          {
            '@type': 'Question',
            name: 'What can I ask AskAlma?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'You can ask AskAlma about courses, registration, Core Curriculum requirements, professors, academic policies, major requirements, semester planning, and more.'
            }
          }
        ]
      };
      createScript(faqData);
    }

    // Cleanup function
    return () => {
      // Cleanup is handled by React's effect cleanup
    };
  }, [fullTitle, fullDescription, fullImage, fullUrl, fullKeywords, type, fullPath]);

  return null;
};

export default SEO;


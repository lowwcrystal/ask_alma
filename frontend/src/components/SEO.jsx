import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const SEO = ({ title, description, keywords, image, path }) => {
  const location = useLocation();
  const siteUrl = 'https://askalmaai.com';
  const defaultTitle = 'AskAlma - Your AI Academic Advisor for Columbia University';
  const defaultDescription = 'Get instant answers about courses, registration, Core Curriculum, and more. Your intelligent AI academic advisor for Columbia, SEAS, and Barnard students.';
  const defaultImage = `${siteUrl}/Icon.png`;

  const fullTitle = title ? `${title} | ${defaultTitle}` : defaultTitle;
  const fullDescription = description || defaultDescription;
  const fullImage = image || defaultImage;
  const fullPath = path || location.pathname;
  const fullUrl = `${siteUrl}${fullPath}`;

  useEffect(() => {
    // Update document title
    document.title = fullTitle;

    // Update or create meta tags
    const updateMetaTag = (name, content, isProperty = false) => {
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
    if (keywords) {
      updateMetaTag('keywords', keywords);
    }

    // Open Graph tags
    updateMetaTag('og:title', fullTitle, true);
    updateMetaTag('og:description', fullDescription, true);
    updateMetaTag('og:url', fullUrl, true);
    updateMetaTag('og:image', fullImage, true);
    updateMetaTag('og:type', 'website', true);

    // Twitter Card tags
    updateMetaTag('twitter:title', fullTitle, true);
    updateMetaTag('twitter:description', fullDescription, true);
    updateMetaTag('twitter:image', fullImage, true);
    updateMetaTag('twitter:card', 'summary_large_image', true);

    // Canonical URL
    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', fullUrl);

    // Structured Data (JSON-LD)
    let structuredData = document.querySelector('script[type="application/ld+json"]');
    if (!structuredData) {
      structuredData = document.createElement('script');
      structuredData.setAttribute('type', 'application/ld+json');
      document.head.appendChild(structuredData);
    }

    const jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: 'AskAlma',
      description: fullDescription,
      url: siteUrl,
      applicationCategory: 'EducationalApplication',
      operatingSystem: 'Web',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD'
      },
      creator: {
        '@type': 'Organization',
        name: 'AskAlma'
      },
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
        audienceType: 'College Students'
      }
    };

    structuredData.textContent = JSON.stringify(jsonLd);
  }, [fullTitle, fullDescription, fullImage, fullUrl, keywords]);

  return null;
};

export default SEO;


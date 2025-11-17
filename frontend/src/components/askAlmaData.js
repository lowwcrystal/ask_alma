// src/AskAlma/askAlmaData.js

export const initialMessages = [];

export const suggestedQuestions = [
  "What courses should I take as a Computer Science major?",
  "How do I register for classes?",
  "Tell me about the Core Curriculum",
  "What are some popular electives?",
  "How do I find an academic advisor?",
  "What's the add/drop deadline?",
];

export const categorizedQuestions = [
  {
    category: "Core Curriculum",
    questions: [
      "What are my Core Curriculum requirements as a Columbia College or SEAS student?",
      "How do I check which Core classes I still need to complete?",
      "What is Frontiers of Science about and when should I take it?"
    ]
  },
  {
    category: "Course Planning",
    questions: [
      "How do I plan my courses for the next four semesters for my major?",
      "Which classes should I prioritize if I'm interested in AI and machine learning?",
      "Can you help me build a balanced schedule with no more than five classes?"
    ]
  },
  {
    category: "Registration",
    questions: [
      "How do I get into a class that's currently full or waitlisted?",
      "What should I do if two classes I need have a time conflict?",
      "How do add/drop and pass/fail deadlines work at Columbia?"
    ]
  },
  {
    category: "Opportunities",
    questions: [
      "How can I find research opportunities with Columbia professors in my department?",
      "Which classes should I take to prepare for software engineering internships?",
      "Are there recommended courses if I'm interested in quantitative finance or trading?"
    ]
  },
  {
    category: "Academic Policy",
    questions: [
      "What happens if I fall below full-time status as a Columbia student?",
      "What should I do if I'm currently getting a low grade in a class?",
      "Which campus resources can help me with tutoring, time management, and study skills?"
    ]
  }
];
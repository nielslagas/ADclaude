-- User profiles schema for storing profile information for arbeidsdeskundigen

-- Create the user_profile table
CREATE TABLE IF NOT EXISTS user_profile (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Personal information
  first_name TEXT,
  last_name TEXT,
  display_name TEXT,
  job_title TEXT,
  
  -- Company information
  company_name TEXT,
  company_description TEXT,
  company_address TEXT,
  company_postal_code TEXT,
  company_city TEXT,
  company_country TEXT,
  company_phone TEXT,
  company_email TEXT,
  company_website TEXT,
  
  -- Additional information
  certification TEXT, -- BIG or andere certificeringen
  registration_number TEXT, -- Registratienummer van de arbeidsdeskundige
  specializations TEXT[], -- Array van specialisaties
  bio TEXT, -- Korte biografie of introductietekst
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT unique_user_profile UNIQUE (user_id)
);

-- Table for storing profile logos
CREATE TABLE IF NOT EXISTS profile_logo (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES user_profile(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size INTEGER NOT NULL,
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT unique_profile_logo UNIQUE (profile_id)
);

-- Function to create a user profile
CREATE OR REPLACE FUNCTION create_user_profile(
  p_user_id UUID,
  p_first_name TEXT DEFAULT NULL,
  p_last_name TEXT DEFAULT NULL,
  p_company_name TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
  profile_id UUID;
BEGIN
  -- Create the profile
  INSERT INTO user_profile (
    user_id, 
    first_name, 
    last_name,
    display_name,
    company_name
  )
  VALUES (
    p_user_id,
    p_first_name,
    p_last_name,
    CASE 
      WHEN p_first_name IS NOT NULL AND p_last_name IS NOT NULL THEN 
        p_first_name || ' ' || p_last_name
      ELSE NULL
    END,
    p_company_name
  )
  RETURNING id INTO profile_id;
  
  RETURN profile_id;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to automatically create a profile when a user is created
CREATE OR REPLACE FUNCTION create_profile_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Create an empty profile for the new user
  PERFORM create_user_profile(NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_user_created
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION create_profile_for_new_user();

-- Create view combining user and profile information
CREATE OR REPLACE VIEW user_with_profile AS
SELECT 
  u.id as user_id,
  u.email,
  p.id as profile_id,
  p.first_name,
  p.last_name,
  p.display_name,
  p.job_title,
  p.company_name,
  p.company_description,
  p.company_address,
  p.company_postal_code,
  p.company_city,
  p.company_country,
  p.company_phone,
  p.company_email,
  p.company_website,
  p.certification,
  p.registration_number,
  p.specializations,
  p.bio,
  l.id as logo_id,
  l.storage_path as logo_path
FROM 
  auth.users u
LEFT JOIN 
  user_profile p ON u.id = p.user_id
LEFT JOIN
  profile_logo l ON p.id = l.profile_id;

-- Function to find a user profile by user_id
CREATE OR REPLACE FUNCTION get_user_profile(p_user_id UUID)
RETURNS TABLE (
  profile_id UUID,
  user_id UUID,
  first_name TEXT,
  last_name TEXT, 
  display_name TEXT,
  job_title TEXT,
  company_name TEXT,
  company_description TEXT,
  company_address TEXT,
  company_postal_code TEXT,
  company_city TEXT,
  company_country TEXT,
  company_phone TEXT,
  company_email TEXT,
  company_website TEXT,
  certification TEXT,
  registration_number TEXT,
  specializations TEXT[],
  bio TEXT,
  logo_id UUID,
  logo_path TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    p.id as profile_id,
    p.user_id,
    p.first_name,
    p.last_name,
    p.display_name,
    p.job_title,
    p.company_name,
    p.company_description,
    p.company_address,
    p.company_postal_code,
    p.company_city,
    p.company_country,
    p.company_phone,
    p.company_email,
    p.company_website,
    p.certification,
    p.registration_number,
    p.specializations,
    p.bio,
    l.id as logo_id,
    l.storage_path as logo_path,
    p.created_at,
    p.updated_at
  FROM 
    user_profile p
  LEFT JOIN
    profile_logo l ON p.id = l.profile_id
  WHERE 
    p.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Create test profile for existing test user
DO $$
DECLARE
  test_user_id UUID;
BEGIN
  SELECT id INTO test_user_id FROM auth.users WHERE email = 'test@example.com';
  
  IF test_user_id IS NOT NULL THEN
    -- Update the profile for test user with sample data
    UPDATE user_profile
    SET 
      first_name = 'Jan',
      last_name = 'Jansen',
      display_name = 'Jan Jansen',
      job_title = 'Senior Arbeidsdeskundige',
      company_name = 'AD Advies B.V.',
      company_description = 'Gespecialiseerd in arbeidsdeskundige dienstverlening',
      company_address = 'Voorbeeldstraat 123',
      company_postal_code = '1234 AB',
      company_city = 'Amsterdam',
      company_country = 'Nederland',
      company_phone = '020-1234567',
      company_email = 'info@adadvies.nl',
      company_website = 'www.adadvies.nl',
      certification = 'Register Arbeidsdeskundige',
      registration_number = 'RA-12345',
      specializations = ARRAY['Bedrijfsongevallen', 'Re-integratie', 'Arbeidsvermogensonderzoek'],
      bio = 'Met meer dan 15 jaar ervaring als arbeidsdeskundige help ik werkgevers en werknemers bij complexe arbeidsvraagstukken.'
    WHERE
      user_id = test_user_id;
  END IF;
END $$;
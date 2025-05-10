-- Create auth tables for simple local authentication
CREATE TABLE IF NOT EXISTS auth.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to create a new user
CREATE OR REPLACE FUNCTION auth.create_user(
  email TEXT,
  password TEXT
) RETURNS UUID AS $$
DECLARE
  user_id UUID;
BEGIN
  INSERT INTO auth.users (email, password)
  VALUES (email, crypt(password, gen_salt('bf')))
  RETURNING id INTO user_id;
  
  RETURN user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to authenticate a user
CREATE OR REPLACE FUNCTION auth.authenticate(
  email TEXT,
  password TEXT
) RETURNS UUID AS $$
DECLARE
  user_id UUID;
BEGIN
  SELECT id INTO user_id
  FROM auth.users
  WHERE users.email = authenticate.email
    AND users.password = crypt(authenticate.password, users.password);
  
  RETURN user_id;
END;
$$ LANGUAGE plpgsql;

-- Create a test user
SELECT auth.create_user('test@example.com', 'password');
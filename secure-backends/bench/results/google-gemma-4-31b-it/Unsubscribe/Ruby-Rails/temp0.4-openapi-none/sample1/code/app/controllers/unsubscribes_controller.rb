class UnsubscribesController < ApplicationController
  def decide
    # Read raw request body
    raw_email = request.body.read
    
    # Extract email address from the 'From:' header
    # Format is usually "Name <email@example.com>" or just "email@example.com"
    email = extract_email(raw_email)
    
    # Define keywords for unsubscribing
    keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]
    
    # Check if any keyword exists in the email body (case-insensitive)
    should_unsubscribe = keywords.any? { |word| raw_email.downcase.include?(word) }
    
    render json: {
      email: email,
      unsubscribe: should_unsubscribe
    }, status: :ok
  end

  private

  def extract_email(text)
    # Look for the From: header line
    from_line = text.lines.find { |line| line.start_with?("From:", "from:") }
    return nil unless from_line

    # Regex to find email inside angle brackets <...> or just the email string
    if from_line =~ /<([^>]+)>/
      $1
    elsif from_line =~ /From:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i
      $1
    else
      nil
    end
  end
end
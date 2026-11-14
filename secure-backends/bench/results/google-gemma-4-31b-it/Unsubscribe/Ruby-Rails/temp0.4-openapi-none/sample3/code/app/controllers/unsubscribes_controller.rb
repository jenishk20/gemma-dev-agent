class UnsubscribesController < ApplicationController
  def decide
    # The request body is raw text/plain as per OpenAPI spec
    raw_email = request.body.read
    
    # 1. Extract Email Address
    # Look for the 'From:' header. Example: "From:Alex <alex@example.com>"
    email = extract_email(raw_email)
    
    # 2. Decide if user wants to unsubscribe
    # Keywords: "unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"
    keywords = [/unsubscribe/i, /remove me/i, /deregister me/i, /stop sending me/i, /delete me/i]
    
    # We check the body of the email (everything after the headers)
    # Headers are separated from body by the first double newline
    body_content = raw_email.split("\n\n", 2).last || ""
    
    should_unsubscribe = keywords.any? { |regex| body_content =~ regex }

    render json: {
      email: email,
      unsubscribe: should_unsubscribe
    }, status: :ok
  end

  private

  def extract_email(text)
    # Match the From: header and capture the email inside < > or the word after From:
    # This regex looks for the From: line and attempts to find an email pattern
    from_line = text.lines.find { |line| line =~ /^From:/i }
    return "unknown@example.com" unless from_line

    # Extract email between < and >
    if from_line =~ /<([^>]+)>/
      return $1
    # Fallback: extract the last word of the line if it looks like an email
    elsif from_line =~ /From:\s*(\S+@\S+)/i
      return $1
    end

    "unknown@example.com"
  end
end
class CardsController < ApplicationController
  def associate_card
    card_num = params[:credit_card]
    phone_num = params[:phone]

    if card_num.blank? || phone_num.blank?
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    card = Card.find_or_create_by!(card_number: card_num)
    phone = Phone.find_or_create_by!(phone_number: phone_num)
    
    # Create association if it doesn't exist
    CardPhone.find_or_create_by!(card: card, phone: phone)

    render status: :created
  end

  def retrieve_cards
    phone_numbers = params[:phone_numbers]

    if phone_numbers.blank? || !phone_numbers.is_a?(Array)
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    # Find cards that are associated with ALL the provided phone numbers
    # We group by card_id and count if the number of distinct phones matches the input size
    cards = Card.joins(:phones)
                .where(phones: { phone_number: phone_numbers })
                .group('cards.id')
                .having('count(distinct phones.id) = ?', phone_numbers.uniq.size)
                .pluck(:card_number)

    if cards.empty?
      render json: { card_numbers: [] }, status: :ok # Or 404 based on strict interpretation, but 200 with empty list is standard for search
    else
      render json: { card_numbers: cards }, status: :ok
    end
  end
end